import json
import stripe
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from .database import save_message, save_user_subscription, check_subscription_status
from .message_handler import process_message_with_donna
from .utils import send_text, send_activation_email, send_failed_cancellation_email
from .subscription_manager import handle_subscription_command, is_subscription_command, extract_subscription_info
from .integrations.auth_utils import verify_oauth_state, exchange_oauth_code, store_oauth_tokens

# Stripe configuration
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
stripe.api_key = os.getenv("STRIPE_API_KEY")


class PostHandler(BaseHTTPRequestHandler):
    """Handle POST requests to the server."""
    
    def do_POST(self):
        """Process incoming POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            
            # Check the path to determine the handler
            if self.path == "/new_message":
                self.handle_new_message(data)
            elif self.path == "/webhooks/stripe":
                self.handle_stripe_webhook(post_data)
            else:
                self.return_bad_request(f"Unknown path: {self.path}")
        except json.JSONDecodeError:
            self.return_bad_request("Invalid JSON data")
        except Exception as e:
            self.return_server_error(str(e))
    
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
        
        # Extract the data
        chat_guid = data["chatGuid"]
        message_data = data["data"]
        
        if "message" not in message_data:
            self.return_bad_request("Missing message data")
            return
        
        # Extract message details
        message_text = message_data["message"].get("text", "")
        message_guid = message_data["message"].get("guid", "")
        sender = message_data["handle"].get("address", "unknown")
        
        # Save the message to the database
        save_message(chat_guid, sender, message_text, message_guid)
        
        # Check if this is a subscription-related command
        if is_subscription_command(message_text):
            subscription_response, payment_link = handle_subscription_command(chat_guid, message_text, sender)
            
            # Return a successful response to the server
            self.return_success()
            
            # The subscription manager will take care of sending the response
            return
        
        # Process the message with Donna
        is_first_message = message_data.get("isFirstMessage", False)
        process_message_with_donna(chat_guid, message_text, data, is_first_message)
        
        # Return a successful response to the server
        self.return_success()
    
    def handle_stripe_webhook(self, post_data):
        """
        Handle a Stripe webhook event.
        
        Args:
            post_data (bytes): The raw POST data
        """
        from .subscription_manager import process_payment_confirmation
        
        # Verify Stripe signature
        sig_header = self.headers.get("Stripe-Signature")
        try:
            event = stripe.Webhook.construct_event(
                post_data, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            self.return_bad_request("Invalid signature")
            return
        
        # Handle checkout.session.completed event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            
            # Extract customer information
            customer_id = session.get("customer")
            subscription_id = session.get("subscription")
            client_reference_id = session.get("client_reference_id")
            
            # Get customer email
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = customer.get("email", "")
                
                # Save the subscription information
                if client_reference_id and subscription_id:
                    # Process the payment confirmation
                    process_payment_confirmation(customer_id, subscription_id)
                    
                    # Save the subscription info to the database
                    save_user_subscription(
                        client_reference_id,     # chat_guid
                        email,                   # user_id
                        subscription_id,         # subscription_id
                        "active",                # status
                        "premium"                # plan_name
                    )
                    
                    # Send an activation email
                    send_activation_email(email, customer.get("name", "User"))
            except Exception as e:
                print(f"Error processing checkout session: {e}")
        
        # Return a successful response to the server
        self.return_success()
    
    def return_success(self):
        """Return a successful response."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success"}).encode())
    
    def return_bad_request(self, message):
        """Return a bad request response."""
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "error", "message": message}).encode())
    
    def return_server_error(self, message):
        """Return a server error response."""
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "error", "message": message}).encode())


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback requests."""
    
    def do_GET(self):
        """Handle GET requests for OAuth callbacks."""
        try:
            # Parse the URL and query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Extract the path to determine the integration
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 3 and path_parts[0] == "oauth":
                integration_name = path_parts[1]
                
                # Check if this is a valid callback
                if path_parts[2] == "callback":
                    self.handle_oauth_callback(integration_name, query_params)
                    return
            
            # If we reach here, it's an invalid path
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())
    
    def handle_oauth_callback(self, integration_name, query_params):
        """
        Handle an OAuth callback.
        
        Args:
            integration_name (str): The name of the integration
            query_params (dict): The query parameters
        """
        # Check if the state parameter is present
        if "state" not in query_params or not query_params["state"][0]:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid state parameter")
            return
        
        # Check if the code parameter is present
        if "code" not in query_params or not query_params["code"][0]:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code")
            return
        
        # Verify the state parameter
        state = query_params["state"][0]
        user_info = verify_oauth_state(state)
        if not user_info:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid or expired state parameter")
            return
        
        # Extract the user ID and verify the integration
        user_id = user_info.get("user_id")
        expected_integration = user_info.get("integration_name")
        if not user_id or expected_integration != integration_name:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid integration or user ID")
            return
        
        # Exchange the authorization code for tokens
        code = query_params["code"][0]
        tokens = exchange_oauth_code(integration_name, code)
        if not tokens:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Failed to exchange authorization code for tokens")
            return
        
        # Store the tokens
        success = store_oauth_tokens(user_id, integration_name, tokens)
        if not success:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Failed to store tokens")
            return
        
        # Get the chat GUID from storage
        # In a real implementation, you would store this in a database
        # Here we'll assume it's part of the user_id
        chat_guid = user_id.split(":")[0] if ":" in user_id else user_id
        
        # Send a confirmation message to the user
        message = f"Successfully connected to {integration_name.capitalize()}! You can now use the integration."
        send_text(chat_guid, message)
        
        # Return a success page
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        # HTML response for the user
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Donna - Authentication Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                h1 {{ color: #4CAF50; }}
                p {{ font-size: 18px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Authentication Successful!</h1>
                <p>You have successfully connected your {integration_name.capitalize()} account to Donna.</p>
                <p>You can now close this window and continue your conversation with Donna.</p>
            </div>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode()) 