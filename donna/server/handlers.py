import json
import tempfile
from http.server import BaseHTTPRequestHandler

from donna.database.models import (
    save_message, 
    get_total_message_count, 
    check_subscription_status,
    get_message_by_guid
)
from donna.messaging.bluebubbles import send_text, share_contact_card, download_attachment
from donna.assistant.openai_client import create_assistant_response, process_image_attachment
from donna.payments.stripe_handler import (
    handle_payment_intent_succeeded,
    handle_payment_intent_failed,
    handle_subscription_deleted,
    verify_stripe_signature
)
from donna.config import (
    WELCOME_MESSAGE,
    PAYMENT_MESSAGE,
    EXPIRED_MESSAGE,
    SECRET_SUBSCRIPTION_ACTIVATION_CODE,
    SECRET_SUBSCRIPTION_DEACTIVATION_CODE,
    ACTIVATION_MESSAGE,
    DEACTIVATION_MESSAGE,
    STRIPE_PAYMENT_LINK
)


class PostHandler(BaseHTTPRequestHandler):
    """
    A POST request handler for BlueBubbles webhooks and Stripe webhooks.
    """
    
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
            self.handle_stripe_webhook()
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
                return self.return_bad_request(str(ex) or "Invalid JSON received")

            self.return_ok()

    def handle_stripe_webhook(self):
        """
        Handles a Stripe webhook request.
        """
        content_length = int(self.headers["Content-Length"])
        payload = self.rfile.read(content_length).decode("utf-8")
        sig_header = self.headers.get("Stripe-Signature")

        event = verify_stripe_signature(payload, sig_header)
        if event is None:
            self.send_response(400)
            self.end_headers()
            return

        # Handle different webhook events
        if (
            event["type"] == "checkout.session.completed"
            or event["type"] == "checkout.session.async_payment_succeeded"
        ):
            payment_intent = event["data"]["object"]
            handle_payment_intent_succeeded(payment_intent)
        elif event["type"] == "checkout.session.async_payment_failed":
            payment_intent = event["data"]["object"]
            handle_payment_intent_failed(payment_intent)
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            handle_subscription_deleted(subscription)

        self.send_response(200)
        self.end_headers()

    def handle_json(self, data):
        """
        Handles a generic JSON object. This function will check the type of the
        event and handle it accordingly.

        Args:
            data (dict): The JSON data
        """
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

        assistant_response = create_assistant_response(
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
                    # Download the attachment
                    attachment_content = download_attachment(attachment['guid'])
                    if attachment_content:
                        # Process and upload to OpenAI
                        return process_image_attachment(attachment_content)
                except Exception as e:
                    print(f"Error processing attachment: {e}")
        return None 