@ -0,0 +1,905 @@
import json
import requests
import openai
import tempfile
import sqlite3
from time import sleep
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timezone
import stripe
import resend
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# BlueBubbles server address and password
server_addr = "http://localhost:1234"
server_password = os.getenv("BLUEBUBBLES_SERVER_PASSWORD")

# OpenAI API key and Alfred's assistant ID
openai.api_key = os.getenv("OPENAI_API_KEY")
alfred_assistant_id = os.getenv("ALFRED_ASSISTANT_ID")

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Stripe configuration (Test mode)
# stripe.api_key = os.getenv("STRIPE_API_KEY_TEST")
# STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET_TEST")

# Resend configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

# Secret codes
SECRET_SUBSCRIPTION_ACTIVATION_CODE = os.getenv("SECRET_SUBSCRIPTION_ACTIVATION_CODE")
SECRET_SUBSCRIPTION_DEACTIVATION_CODE = os.getenv(
    "SECRET_SUBSCRIPTION_DEACTIVATION_CODE"
)

PAYMENT_MESSAGE = (
    f"You've reached the maximum number of free messages. "
    f"To continue using me, please subscribe using this link: "
    f"{STRIPE_PAYMENT_LINK}"
)

WELCOME_MESSAGE = """
Hey! I'm Alfred, your personal COO. Here's what I can do for you:

- Manage tasks & schedule: Share your tasks, and I'll help prioritize and organize your schedule.
- Reminders: Set deadlines, and I'll remind you when needed.
- Integration: Google Calendar, Notion, and more.
- Ask me anything: I'm an AI you can text — I'm here 24/7 if you need anything.

Let's get started! What's the first thing you want to tackle today?
"""

ACTIVATION_MESSAGE = (
    "Congratulations! Your subscription has been activated. "
    "You now have unlimited access to me. Enjoy!"
)
DEACTIVATION_MESSAGE = (
    "Your subscription has been deactivated. "
    f"Please consider subscribing again to continue using me: {STRIPE_PAYMENT_LINK}"
)
EXPIRED_MESSAGE = (
    "Your subscription has expired. To continue using me, please renew your subscription "
    f"using this link: {STRIPE_PAYMENT_LINK}"
)
SUBSCRIPTION_CANCELLATION_MESSAGE = (
    "Your subscription has been cancelled. To continue using me, please renew your subscription "
    f"using this link: {STRIPE_PAYMENT_LINK}"
)


# SQLite database setup
def init_db():
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS conversations
                 (chat_guid TEXT PRIMARY KEY, thread_id TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_guid TEXT,
                  sender TEXT,
                  message TEXT,
                  message_guid TEXT UNIQUE,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (chat_guid) REFERENCES conversations(chat_guid))"""
    )
    conn.commit()
    conn.close()


# Initialize the users database
def init_users_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS subscriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT UNIQUE,
                  email TEXT,
                  status TEXT,
                  subscription_date TIMESTAMP)"""
    )
    conn.commit()
    conn.close()


# Get a thread ID from the database
def get_thread_id(chat_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("SELECT thread_id FROM conversations WHERE chat_guid = ?", (chat_guid,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# Save a thread ID to the database
def save_thread_id(chat_guid, thread_id):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO conversations (chat_guid, thread_id, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (chat_guid, thread_id),
    )
    conn.commit()
    conn.close()


# Save a message to the database
def save_message(chat_guid, sender, message, message_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (chat_guid, sender, message, message_guid) VALUES (?, ?, ?, ?)",
        (chat_guid, sender, message, message_guid),
    )
    conn.commit()
    conn.close()


# Retrieve recent messages
def get_recent_messages(chat_guid, limit=10):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT sender, message FROM messages 
        WHERE chat_guid = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """,
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    return list(reversed(messages))  # Reverse to get chronological order


# Get a message by its GUID:
def get_message_by_guid(message_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT sender, message FROM messages WHERE message_guid = ?", (message_guid,)
    )
    result = c.fetchone()
    conn.close()
    return result


# Get the number of messages Alfred has sent in a chat:
def get_total_message_count(chat_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM messages WHERE chat_guid = ?",
        (chat_guid,),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


# Save user subscription information:
def save_user_subscription(status, phone_number=None, email=None):
    if not phone_number and not email:
        raise ValueError("Either phone_number or email must be provided")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO subscriptions 
           (phone_number, email, status, subscription_date) 
           VALUES (?, ?, ?, ?)""",
        (phone_number, email, status, datetime.now(timezone.utc)),
    )
    conn.commit()
    conn.close()


def find_latest_chat_guid(identifier):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT chat_guid FROM messages 
        WHERE sender = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """,
        (identifier,),
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def send_activation_email(to_email, name):
    subject = "Action Required: Activate Your Alfred Subscription"
    body = f"""
    Hi {name},<br /><br />

    I was unable to find the iMessage account associated with the email ({to_email}) linked to your Stripe payment.<br /><br />
    
    <b>To activate me, please reply to this email with your iMessage account (either phone number or email).</b><br /><br />
    
    If you have any questions, feel free to contact our support team at team@gtfol.inc.<br /><br />

    Best,<br />
    Alfred<br /><br />

    <a href="https://alfredagent.com">Alfred — Your In-House COO</a>
    """

    try:
        resend.Emails.send(
            {
                "from": "Alfred <alfred@mail.gtfol.inc>",
                "to": [to_email],
                "cc": ["team@gtfol.inc"],
                "subject": subject,
                "html": body,
            }
        )
        print(f"Notification email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send notification email: {e}")


def send_failed_cancellation_email(name, email, phone_number):
    subject = "Failed: Alfred Subscription Cancellation"
    body = f"""
    Hi,<br /><br />

    The user <b>{name}</b> has cancelled their Alfred subscription. However, I was unable to update the subscription status in my database. Please check the user's details and update the status manually.<br /><br />

    Here are the details of the user:<br />
    <ul>
        <li>Name: {name}</li>
        <li>Email: {email}</li>
        <li>Phone Number: {phone_number}</li>
    </ul><br /><br />

    Best,<br />
    Alfred<br /><br />

    <a href="https://alfredagent.com">Alfred — Your In-House COO</a>
    """

    try:
        resend.Emails.send(
            {
                "from": "Alfred <alfred@mail.gtfol.inc>",
                "to": ["team@gtfol.inc"],
                "subject": subject,
                "html": body,
            }
        )
        print(f"Notification email sent to team@gtfol.inc")
    except Exception as e:
        print(f"Failed to send notification email: {e}")


def check_subscription_status(phone_number=None, email=None):
    if not phone_number and not email:
        return None
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    if phone_number:
        c.execute(
            "SELECT status FROM subscriptions WHERE phone_number = ?", (phone_number,)
        )
    elif email:
        c.execute("SELECT status FROM subscriptions WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# Initialize both databases
init_db()
init_users_db()


def send_text(chat_guid, message, method="private-api"):
    """
    Sends a text message to a chat via the BlueBubbles server.

    Args:
        chat_guid (str): The chat guid to send the message to
        message (str): The text to send
        method (str): The method to use to send the message. Defaults to "private-api"

    Returns:
        str: The message_guid of the sent message, or None if an error occurred
    """
    params = {"password": server_password}
    data = {"chatGuid": chat_guid, "message": message, "method": method}

    try:
        response = requests.post(
            f"{server_addr}/api/v1/message/text",
            json=data,
            params=params,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        # print(f"Message sent successfully. Response: {response.text}")

        # Parse the response to get the message_guid
        response_data = response.json()
        return response_data.get("data", {}).get("guid")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e.response, "text"):
            print(f"Response content: {e.response.text}")
        return None


def share_contact_card(chat_guid):
    """
    Shares Alfred's contact card with the user via the BlueBubbles API.

    Args:
        chat_guid (str): The chat GUID to share the contact card with

    Returns:
        bool: True if the contact card was shared successfully, False otherwise
    """
    params = {"password": server_password}

    try:
        response = requests.post(
            f"{server_addr}/api/v1/chat/{chat_guid}/share/contact",
            json={},
            params=params,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sharing contact card: {e}")
        return False


class StripeWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        payload = self.rfile.read(content_length).decode("utf-8")
        sig_header = self.headers.get("Stripe-Signature")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            print("Invalid payload")
            self.send_response(400)
            self.end_headers()
            return
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            print("Invalid signature")
            self.send_response(400)
            self.end_headers()
            return

        if (
            event["type"] == "checkout.session.completed"
            or event["type"] == "checkout.session.async_payment_succeeded"
        ):
            print("Payment succeeded")
            payment_intent = event["data"]["object"]
            self.handle_payment_intent_succeeded(payment_intent)
        elif event["type"] == "checkout.session.async_payment_failed":
            payment_intent = event["data"]["object"]
            self.handle_payment_intent_failed(payment_intent)
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            self.handle_subscription_deleted(subscription)

        self.send_response(200)
        self.end_headers()


# Create a class to handle a POST request on port 4321
class PostHandler(BaseHTTPRequestHandler):

    def return_bad_request(self, error="Bad Request"):
        """
        A function to return a 400 error.

        Args:
            error (str): The error message to return
        """

        self.send_response(400)
        self.end_headers()
        self.wfile.write(error.encode("utf-8"))

    def return_ok(self, message="OK"):
        """
        A function to return a 200 response.

        Args:
            message (str): The message to return
        """

        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def do_POST(self):
        """
        A POST request handler. This is called when a POST request is received.
        This function does some validation around "valid" requests relative to
        what the BlueBubbles server will emit via Webhooks.
        """

        if self.path == "/stripe-webhook":
            StripeWebhookHandler.do_POST(self)
        else:
            # Ignore any request that isn't JSON
            if self.headers["Content-Type"] != "application/json":
                return self.return_bad_request()

            # Read the data
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            try:
                # Convert the data to a JSON object and pass it to the handler
                data = json.loads(post_data)

                print("📩 Received JSON data: ", data)

                self.handle_json(data)
            except ValueError as ex:
                return self.return_bad_request(ex.message or "Invalid JSON received")

            self.return_ok()

    def handle_json(self, data):
        """
        Handles a generic JSON object. This function will check the type of the
        event and handle it accordingly.

        Args:
            data (dict): The JSON data
        """

        # print("📩 Received JSON data: ", data)

        if data.get("type") == "new-message":
            self.handle_new_message(data)
        else:
            print("❓ Unhandled event type: ", data.get("type"))

    def handle_new_message(self, data):
        """
        Handles a new-message event.
        This function will now process the message with Alfred and respond accordingly.

        Args:
            data (dict): The JSON data
        """

        if not isinstance(data.get("data"), dict):
            return

        # Extract the chat guid and message text
        chats = data.get("data").get("chats", [])
        if not chats:
            raise ValueError("No chats found in data")

        chat_guid = chats[0].get("guid")
        message_text = data.get("data").get("text", "")
        is_from_me = data.get("data").get("isFromMe", False)
        sender = (
            "alfred@gtfol.inc"
            if is_from_me
            else data.get("data").get("handle", {}).get("address", "Unknown")
        )

        if not is_from_me and sender != "Unknown":
            if sender.startswith("+"):
                phone_number = sender
                email = None
            else:
                phone_number = None
                email = sender
        else:
            phone_number = None
            email = None

        message_guid = data.get("data", {}).get("guid")
        thread_originator_guid = data.get("data", {}).get("threadOriginatorGuid")

        # Ignore messages that I sent
        if is_from_me:
            return

        # Check if this is the first message from the user
        is_first_message = get_total_message_count(chat_guid) == 0

        # Save the incoming message to the database
        save_message(chat_guid, sender, message_text, message_guid)

        # Check if this is a group chat based on the GUID format
        is_group_chat = chat_guid.startswith("iMessage;+;")

        # Check if this is a reply to a message
        is_reply = thread_originator_guid is not None
        is_reply_to_alfred = False

        if is_reply:
            original_message = get_message_by_guid(thread_originator_guid)
            if original_message:
                original_sender, original_text = original_message
                is_reply_to_alfred = original_sender == "alfred@gtfol.inc"

        # Check if this is the secret code
        if message_text.strip() == SECRET_SUBSCRIPTION_ACTIVATION_CODE:
            save_user_subscription(
                status="active", phone_number=phone_number, email=email
            )
            alfred_message_guid = send_text(chat_guid, ACTIVATION_MESSAGE)
            if alfred_message_guid:
                save_message(
                    chat_guid,
                    "alfred@gtfol.inc",
                    ACTIVATION_MESSAGE,
                    alfred_message_guid,
                )
                print(f"Subscription activated for phone number: {phone_number}")
            else:
                print(f"Failed to send activation message to chat_guid: {chat_guid}")
            return

        # Check if this is the secret code
        if message_text.strip() == SECRET_SUBSCRIPTION_DEACTIVATION_CODE:
            save_user_subscription(
                status="expired", phone_number=phone_number, email=email
            )
            alfred_message_guid = send_text(chat_guid, DEACTIVATION_MESSAGE)
            if alfred_message_guid:
                save_message(
                    chat_guid,
                    "alfred@gtfol.inc",
                    DEACTIVATION_MESSAGE,
                    alfred_message_guid,
                )
                print(f"Subscription deactivated for chat_guid: {chat_guid}")
            else:
                print(f"Failed to send activation message to chat_guid: {chat_guid}")
            return

        # Check Alfred's message count for this chat
        alfred_message_count = get_total_message_count(chat_guid)

        # Check the subscription status
        subscription_status = check_subscription_status(
            phone_number=phone_number, email=email
        )

        if subscription_status == "active":
            # User has an active subscription, process the message normally
            self.process_message_with_alfred(
                chat_guid, message_text, data, is_first_message
            )
        elif subscription_status == "expired":
            alfred_message_guid = send_text(chat_guid, EXPIRED_MESSAGE)
            if alfred_message_guid:
                print("Expiration notice sent")
            else:
                print("Failed to send expiration notice")
        elif alfred_message_count >= 30:
            alfred_message_guid = send_text(chat_guid, PAYMENT_MESSAGE)
            if alfred_message_guid:
                print("Payment request message sent")
            else:
                print("Failed to send payment request message")
        else:
            # Process the message with Alfred (for users under the message limit)
            self.process_message_with_alfred(
                chat_guid, message_text, data, is_first_message
            )

    def send_welcome_message(self, chat_guid):
        """
        Sends the welcome message to a new user.

        Args:
            chat_guid (str): The chat GUID to send the message to
        """
        # Share Alfred's contact card
        contact_card_shared = share_contact_card(chat_guid)
        if contact_card_shared:
            print(f"Contact card shared with chat_guid: {chat_guid}")
        else:
            print(f"Failed to share contact card with chat_guid: {chat_guid}")

        # Send welcome message
        alfred_message_guid = send_text(chat_guid, WELCOME_MESSAGE)
        if alfred_message_guid:
            save_message(
                chat_guid,
                "alfred@gtfol.inc",
                WELCOME_MESSAGE,
                alfred_message_guid,
            )
            print(f"Welcome message sent to chat_guid: {chat_guid}")
        else:
            print(f"Failed to send welcome message to chat_guid: {chat_guid}")

    def process_message_with_alfred(
        self, chat_guid, message_text, data, is_first_message
    ):
        """
        Processes a message with Alfred.

        Args:
            chat_guid (str): The chat GUID for the conversation
            message_text (str): The message to process
            data (dict): The data
            is_first_message (bool): Whether this is the first message
        """

        if is_first_message:
            self.send_welcome_message(chat_guid)
            return

        attachments = data.get("data").get("attachments", [])
        file_id = None
        if attachments:
            file_id = self.process_attachments(attachments)

        print("Detected incoming message... Processing with Alfred...")

        assistant_response = self.create_alfred_response(
            chat_guid, message_text, file_id, chat_guid.startswith("iMessage;+;")
        )

        print("Dispatching Alfred's response...")
        alfred_message_guid = send_text(chat_guid, assistant_response)
        if alfred_message_guid:
            # Only save the message if it's not the payment link response
            if STRIPE_PAYMENT_LINK not in assistant_response:
                save_message(
                    chat_guid,
                    "alfred@gtfol.inc",
                    assistant_response,
                    alfred_message_guid,
                )
                print("Response dispatched and saved")
            else:
                print("Payment request message sent")
        else:
            print("Failed to get message_guid for Alfred's response")

    def process_attachments(self, attachments):
        """
        Processes attachments and uploads image to OpenAI if available.

        Args:
            attachments (list): List of attachment dictionaries

        Returns:
            str: OpenAI file ID or None
        """
        for attachment in attachments:
            if attachment.get("mimeType", "").startswith("image/"):
                try:
                    # Parameters for image resizing and quality
                    params = {
                        "password": server_password,
                        "width": 800,  # Adjust this value as needed
                        "height": 800,  # Adjust this value as needed
                        "quality": "better",
                    }

                    response = requests.get(
                        f"{server_addr}/api/v1/attachment/{attachment['guid']}/download",
                        params=params,
                    )
                    response.raise_for_status()

                    # Save the image to a temporary file
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".jpg"
                    ) as temp_file:
                        temp_file.write(response.content)
                        temp_file_path = temp_file.name

                    # Upload the image to OpenAI
                    with open(temp_file_path, "rb") as file:
                        openai_file = openai.files.create(file=file, purpose="vision")

                    return openai_file.id
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading attachment: {e}")
                except Exception as e:
                    print(f"Error uploading file to OpenAI: {e}")
        return None

    def create_alfred_response(
        self, chat_guid, message, file_id=None, is_group_chat=False
    ):
        """
        Creates a response from Alfred using the OpenAI API.

        Args:
            chat_guid (str): The chat GUID for the conversation
            message (str): The message to process
            file_id (str): OpenAI file ID for the image, if available
            is_group_chat (bool): Whether this is a group chat

        Returns:
            str: Alfred's response
        """
        try:
            # Check if there's an existing thread for this conversation
            thread_id = get_thread_id(chat_guid)
            if thread_id:
                thread = openai.beta.threads.retrieve(thread_id)
            else:
                thread = openai.beta.threads.create()
                save_thread_id(chat_guid, thread.id)

            # Create message content
            content = []

            # If it's a group chat, include recent messages for context
            if is_group_chat:
                recent_messages = get_recent_messages(chat_guid, 15)
                if recent_messages:
                    context = "Here are the recent messages in the group chat:\n\n"
                    for sender, msg in recent_messages:
                        context += f"{sender}: {msg}\n"
                    context += "\nPlease consider this context when responding to the following message:\n"
                    content.append({"type": "text", "text": context})

            if message:
                content.append({"type": "text", "text": message})
            elif file_id:
                content.append(
                    {
                        "type": "text",
                        "text": "Please look at this image and provide your thoughts on it.",
                    }
                )

            if file_id:
                content.append(
                    {"type": "image_file", "image_file": {"file_id": file_id}}
                )

            openai.beta.threads.messages.create(
                thread_id=thread.id, role="user", content=content
            )

            run = openai.beta.threads.runs.create(
                thread_id=thread.id, assistant_id=alfred_assistant_id
            )

            # Wait for the run to complete
            while run.status != "completed":
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id, run_id=run.id
                )
                sleep(1)

            # Retrieve Alfred's response
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            alfred_response = messages.data[0].content[0].text.value

            return alfred_response
        except Exception as e:
            print(f"❌ Error processing message with Alfred: {e}")
            return "I'm sorry, I encountered an error while processing your message."

    def handle_payment_intent_succeeded(self, payment_intent):
        try:
            print("Payment succeeded")

            # Extract user information from the payment intent
            customer = stripe.Customer.retrieve(payment_intent["customer"])
            phone_number = customer.phone
            email = customer.email
            name = customer.name

            # TODO: Save the user's contact

            # Save user subscription information
            save_user_subscription(
                status="active", phone_number=phone_number, email=email
            )

            # Find chat_guid
            chat_guid = None
            if phone_number:
                chat_guid = find_latest_chat_guid(phone_number)
            elif email:
                chat_guid = find_latest_chat_guid(email)

            if chat_guid:
                # Send activation message
                alfred_message_guid = send_text(chat_guid, ACTIVATION_MESSAGE)
                if alfred_message_guid:
                    print(f"Activation message sent to user: {email}")
                else:
                    print(f"Failed to send activation message to user: {email}")
            elif email:
                # Send activation email
                send_activation_email(email, name)
            else:
                print(f"💳 No chat_guid or email found for customer: {customer}")
        except Exception as e:
            print(f"Error handling successful payment intent: {e}")

    def handle_payment_intent_failed(self, payment_intent):
        # Extract user information from the payment intent
        customer = stripe.Customer.retrieve(payment_intent["customer"])

        print(f"💳 Payment failed for customer: {customer}")

    def handle_subscription_deleted(self, subscription):
        # Extract user information from the subscription
        customer = stripe.Customer.retrieve(subscription["customer"])

        phone_number = customer.phone
        email = customer.email
        name = customer.name

        # Save user subscription information
        save_user_subscription(status="expired", phone_number=phone_number, email=email)

        # Find chat_guid
        chat_guid = None
        if phone_number:
            chat_guid = find_latest_chat_guid(phone_number)
        elif email:
            chat_guid = find_latest_chat_guid(email)

        if chat_guid:
            # Send activation message
            alfred_message_guid = send_text(
                chat_guid, SUBSCRIPTION_CANCELLATION_MESSAGE
            )
            if alfred_message_guid:
                print(f"Subscription cancellation message sent to user: {email}")
            else:
                print(
                    f"Failed to send subscription cancellation message to user: {email}"
                )
        elif email:
            # Send failed cancellation email
            send_failed_cancellation_email(email, name)
        else:
            print(f"💳 No chat_guid or email found for customer: {customer}")

        print(f"Subscription deleted: {subscription}")


# Create a threaded HTTP server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


# Create a threaded server on port 4321
server = ThreadedHTTPServer(("", 4321), PostHandler)
print("Threaded server started on port 4321")
server.serve_forever()