import json
import stripe
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

from src.models.llm_manager import LLMManager
from src.services.messaging import MessagingService
from src.database.db_manager import (
    save_message,
    get_thread_id,
    get_recent_messages,
    check_subscription_status,
    save_user_subscription,
    find_latest_chat_guid,
)
from src.services.email_service import EmailService
from src.config.settings import (
    STRIPE_WEBHOOK_SECRET,
    PAYMENT_MESSAGE,
    WELCOME_MESSAGE,
    ACTIVATION_MESSAGE,
    DEACTIVATION_MESSAGE,
)


class WebhookHandler(BaseHTTPRequestHandler):
    """Base class for webhook handlers with common utility methods."""
    
    def return_bad_request(self, error="Bad Request"):
        """Return a 400 Bad Request response."""
        self.send_response(400)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": error}).encode("utf-8"))

    def return_ok(self, message="OK"):
        """Return a 200 OK response."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"message": message}).encode("utf-8"))


class MessageWebhookHandler(WebhookHandler):
    """Handler for incoming message webhook requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm_manager = LLMManager()
        self.messaging_service = MessagingService()
        self.email_service = EmailService()
        
    def do_POST(self):
        """Handle POST requests for incoming messages."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        # Handle different content types
        content_type = self.headers.get("Content-Type", "")
        
        if content_type.startswith("application/json"):
            try:
                data = json.loads(post_data)
                self.handle_json(data)
            except json.JSONDecodeError:
                self.return_bad_request("Invalid JSON")
        elif content_type.startswith("application/x-www-form-urlencoded"):
            data = parse_qs(post_data)
            # Convert array values to single strings where needed
            processed_data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
            self.handle_json(processed_data)
        else:
            self.return_bad_request("Unsupported Content-Type")
            
    def handle_json(self, data):
        """Process JSON data based on the type of event."""
        # Check for message type
        if "type" in data:
            event_type = data["type"]
            
            if event_type == "message.received":
                self.handle_new_message(data)
            else:
                self.return_ok(f"Unhandled event type: {event_type}")
        else:
            self.return_bad_request("Missing event type")
            
    def handle_new_message(self, data):
        """Process a new incoming message."""
        # Extract necessary data from the event
        chat_guid = data.get("chatGuid", "")
        message_text = data.get("text", "")
        sender = data.get("handle", {}).get("address", "Unknown")
        message_guid = data.get("guid", "")
        
        if not chat_guid or not message_guid:
            self.return_bad_request("Missing required fields")
            return
            
        # Save message to database
        save_message(chat_guid, sender, message_text, message_guid)
        
        # Check if this is a message we should respond to
        if self.should_process_message(data):
            # Check if this is the first message in the conversation
            is_first_message = not get_thread_id(chat_guid)
            
            # Process the message
            self.process_message_with_assistant(
                chat_guid, message_text, data, is_first_message
            )
            
        # Return a success response
        self.return_ok("Message processed")
        
    def should_process_message(self, data):
        """Determine if we should process this message."""
        # Don't process messages from ourselves
        if data.get("isFromMe", False):
            return False
            
        # Check other conditions as needed (e.g., group chat settings, etc.)
        
        return True
        
    def process_message_with_assistant(
        self, chat_guid, message_text, data, is_first_message
    ):
        """Process a message with the AI assistant."""
        # Get chat details to check if it's a group chat
        is_group_chat = False
        try:
            chat_details = self.messaging_service.get_chat_details(chat_guid)
            if chat_details:
                is_group_chat = chat_details.get("isGroup", False)
        except Exception as e:
            print(f"Error getting chat details: {e}")
            
        # Process attachments if present
        file_data = None
        if "attachments" in data and data["attachments"]:
            try:
                file_data = self.process_attachments(data["attachments"])
            except Exception as e:
                print(f"Error processing attachments: {e}")
                
        # Check if this is a first-time user and send welcome message
        if is_first_message:
            self.send_welcome_message(chat_guid)
            return
            
        # Check subscription status based on phone number or email
        phone_number = data.get("handle", {}).get("address", "")
        subscription_active = check_subscription_status(phone_number=phone_number)
        
        # Count messages for free tier users
        if not subscription_active:
            # If too many messages, send payment message
            # This logic can be expanded or modified as needed
            self.messaging_service.send_text(chat_guid, PAYMENT_MESSAGE)
            return
            
        # Process message with AI
        response = self.create_assistant_response(
            chat_guid, message_text, file_data, is_group_chat
        )
        
        # Send response back to the user
        if response:
            self.messaging_service.send_text(chat_guid, response)
            
    def send_welcome_message(self, chat_guid):
        """Send a welcome message for new conversations."""
        self.messaging_service.send_text(chat_guid, WELCOME_MESSAGE)
        
    def process_attachments(self, attachments):
        """Process attachments and return image data if available."""
        for attachment in attachments:
            if attachment.get("mimeType", "").startswith("image/"):
                try:
                    # Get the attachment
                    attachment_guid = attachment["guid"]
                    image_data = self.messaging_service.download_attachment(attachment_guid)
                    return image_data
                except Exception as e:
                    print(f"Error downloading attachment: {e}")
        return None
        
    def create_assistant_response(
        self, chat_guid, message, image_data=None, is_group_chat=False
    ):
        """Create a response from the AI assistant."""
        try:
            # Get recent messages for context
            chat_history = []
            if is_group_chat:
                recent_messages = get_recent_messages(chat_guid, 15)
                if recent_messages:
                    for sender, msg in recent_messages:
                        chat_history.append({
                            "role": "user" if sender != "assistant" else "assistant",
                            "content": msg
                        })
            
            # Generate system message
            system_message = "You are Alfred, a helpful personal assistant. You are friendly, polite, and professional."
            
            # Process the message with the LLM
            response = self.llm_manager.process_message(
                message=message,
                system_message=system_message,
                chat_history=chat_history,
                image_data=image_data
            )
            
            return response["content"]
        except Exception as e:
            print(f"Error processing message with assistant: {e}")
            return "I'm sorry, I encountered an error while processing your message."


class StripeWebhookHandler(WebhookHandler):
    """Handler for Stripe webhook events."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messaging_service = MessagingService()
        self.email_service = EmailService()
        
    def do_POST(self):
        """Handle POST requests from Stripe webhook."""
        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)
        sig_header = self.headers.get("Stripe-Signature", "")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            print(f"Invalid payload: {e}")
            self.return_bad_request("Invalid payload")
            return
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            self.return_bad_request("Invalid signature")
            return
            
        # Handle the event
        if event["type"] == "payment_intent.succeeded":
            self.handle_payment_intent_succeeded(event["data"]["object"])
        elif event["type"] == "payment_intent.payment_failed":
            self.handle_payment_intent_failed(event["data"]["object"])
        elif event["type"] == "customer.subscription.deleted":
            self.handle_subscription_deleted(event["data"]["object"])
        else:
            print(f"Unhandled event type: {event['type']}")
            
        # Return a success response
        self.return_ok()
        
    def handle_payment_intent_succeeded(self, payment_intent):
        """Handle a successful payment intent."""
        # Extract customer information
        customer_id = payment_intent.get("customer", "")
        if not customer_id:
            print("No customer ID found in payment intent")
            return
            
        try:
            # Get customer details from Stripe
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email", "")
            phone = customer.get("phone", "")
            name = customer.get("name", "")
            
            # Save the subscription in the database
            save_user_subscription(True, phone_number=phone, email=email)
            
            # Send activation message
            if phone:
                # Find the chat GUID associated with this phone number
                chat_guid = find_latest_chat_guid(phone)
                if chat_guid:
                    self.messaging_service.send_text(chat_guid, ACTIVATION_MESSAGE)
                    
            # Send activation email
            if email:
                self.email_service.send_activation_email(email, name)
                
        except Exception as e:
            print(f"Error processing payment intent: {e}")
            
    def handle_payment_intent_failed(self, payment_intent):
        """Handle a failed payment intent."""
        # Extract customer information
        customer_id = payment_intent.get("customer", "")
        if not customer_id:
            print("No customer ID found in payment intent")
            return
            
        try:
            # Get customer details from Stripe
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email", "")
            name = customer.get("name", "")
            
            # Send email about failed payment
            if email:
                self.email_service.send_payment_failed_email(name, email)
                
        except Exception as e:
            print(f"Error processing failed payment intent: {e}")
            
    def handle_subscription_deleted(self, subscription):
        """Handle a subscription deletion."""
        # Extract customer information
        customer_id = subscription.get("customer", "")
        if not customer_id:
            print("No customer ID found in subscription")
            return
            
        try:
            # Get customer details from Stripe
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email", "")
            phone = customer.get("phone", "")
            name = customer.get("name", "")
            
            # Update subscription status in database
            save_user_subscription(False, phone_number=phone, email=email)
            
            # Send deactivation message
            if phone:
                # Find the chat GUID associated with this phone number
                chat_guid = find_latest_chat_guid(phone)
                if chat_guid:
                    self.messaging_service.send_text(
                        chat_guid, DEACTIVATION_MESSAGE
                    )
            elif email:
                # Send email about subscription cancellation
                self.email_service.send_failed_cancellation_email(name, email)
            else:
                print(f"No chat_guid or email found for customer: {customer}")
                
            print(f"Subscription deleted: {subscription}")
            
        except Exception as e:
            print(f"Error processing subscription deletion: {e}") 