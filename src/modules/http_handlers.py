import json
import stripe
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone

from .database import save_message, save_user_subscription, check_subscription_status
from .message_handler import process_message_with_alfred
from .utils import send_activation_email, send_failed_cancellation_email

# Stripe configuration
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class StripeWebhookHandler(BaseHTTPRequestHandler):
    """Handler for Stripe webhook events."""
    
    def do_POST(self):
        """Handle POST requests for Stripe webhooks."""
        content_length = int(self.headers["Content-Length"])
        payload = self.rfile.read(content_length)
        
        sig_header = self.headers.get("Stripe-Signature")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            
            # Handle the event based on its type
            if event["type"] == "payment_intent.succeeded":
                self.handle_payment_intent_succeeded(event["data"]["object"])
            elif event["type"] == "payment_intent.payment_failed":
                self.handle_payment_intent_failed(event["data"]["object"])
            elif event["type"] == "customer.subscription.deleted":
                self.handle_subscription_deleted(event["data"]["object"])
            
            # Return a 200 response to Stripe
            self.send_response(200)
            self.end_headers()
            
        except Exception as e:
            print(f"Error handling Stripe webhook: {e}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Webhook Error")
    
    def handle_payment_intent_succeeded(self, payment_intent):
        """
        Handle a successful payment intent.
        
        Args:
            payment_intent (dict): The payment intent data
        """
        try:
            print("Payment succeeded")

            # Extract user information from the payment intent
            customer = stripe.Customer.retrieve(payment_intent["customer"])
            phone_number = customer.phone
            email = customer.email
            name = customer.name

            # Save user subscription information
            save_user_subscription(
                status="active", phone_number=phone_number, email=email
            )

            # Send an activation email
            send_activation_email(email, name)

            print(f"Subscription activated for {name} ({email}, {phone_number})")
        except Exception as e:
            print(f"Error handling payment intent succeeded: {e}")
    
    def handle_payment_intent_failed(self, payment_intent):
        """
        Handle a failed payment intent.
        
        Args:
            payment_intent (dict): The payment intent data
        """
        # Extract user information from the payment intent
        pass
        
    def handle_subscription_deleted(self, subscription):
        """
        Handle a deleted subscription.
        
        Args:
            subscription (dict): The subscription data
        """
        # Extract user information from the subscription
        pass


class PostHandler(BaseHTTPRequestHandler):
    """Handler for POST requests to the server."""
    
    def return_bad_request(self, error="Bad Request"):
        """
        Return a 400 Bad Request response.
        
        Args:
            error (str): The error message
        """
        self.send_response(400)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": error}).encode())
    
    def return_ok(self, message="OK"):
        """
        Return a 200 OK response.
        
        Args:
            message (str): The response message
        """
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"message": message}).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        # Get content length and read the request body
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            
            # Check if the path is for Stripe webhooks
            if self.path == "/webhook/stripe":
                # Pass the request to the Stripe webhook handler
                StripeWebhookHandler.do_POST(self)
                return
            
            # Parse the request body as JSON
            data = json.loads(post_data.decode("utf-8"))
            
            # Handle the request
            self.handle_json(data)
            
        except Exception as e:
            print(f"Error handling POST request: {e}")
            self.return_bad_request(str(e))
    
    def handle_json(self, data):
        """
        Handle a JSON request.
        
        Args:
            data (dict): The request data
        """
        # Check if the request contains message-related data
        if "chatGuid" in data and "data" in data:
            self.handle_new_message(data)
        else:
            self.return_bad_request("Invalid request format")
    
    def handle_new_message(self, data):
        """
        Handle a new message.
        
        Args:
            data (dict): The message data
        """
        # Check if the request contains the required fields
        if "chatGuid" not in data or "data" not in data:
            self.return_bad_request("Missing required fields")
            return

        # Extract message data
        chat_guid = data["chatGuid"]
        message_text = data.get("data", {}).get("text", "")
        message_guid = data.get("data", {}).get("guid", "")
        sender = data.get("data", {}).get("handle", {}).get("address", "unknown")
        is_from_me = data.get("data", {}).get("isFromMe", False)
        
        # Skip messages that are from me
        if is_from_me:
            self.return_ok("Skipping message from me")
            return
        
        # Check message type and determine if this is the first message
        message_type = data.get("type", "")
        is_first_message = message_type == "chat-created" or message_type == "check-manually"
        
        # Save the message to the database
        if message_guid and message_text:
            save_message(chat_guid, sender, message_text, message_guid)
            print(f"Message saved: {message_text}")
        
        # Check subscription status
        subscription_status = check_subscription_status(email=sender)
        if not subscription_status or subscription_status != "active":
            # TODO: Handle inactive subscription
            print(f"Inactive subscription for {sender}")

        # Process the message with Alfred
        process_message_with_alfred(chat_guid, message_text, data, is_first_message)
        
        # Return success
        self.return_ok("Message received") 