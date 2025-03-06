import json
from http.server import BaseHTTPRequestHandler
from time import sleep
import stripe

from config import STRIPE_WEBHOOK_SECRET, ACTIVATION_MESSAGE, DEACTIVATION_MESSAGE, EXPIRED_MESSAGE, SUBSCRIPTION_CANCELLATION_MESSAGE
from db.db_setup import (get_total_message_count, save_message, get_message_by_guid, save_user_subscription, get_thread_id, save_thread_id, find_latest_chat_guid)
from integrations.messaging import send_text, send_welcome_message, process_attachments, share_contact_card
from llm.llm_handler import create_conversation_chain, generate_response

# Initialize a conversation chain instance
conversation_chain = create_conversation_chain()


class StripeWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        payload = self.rfile.read(content_length).decode("utf-8")
        sig_header = self.headers.get("Stripe-Signature")
        
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return
        except stripe.error.SignatureVerificationError:
            self.send_response(400)
            self.end_headers()
            return

        if event["type"] in ["checkout.session.completed", "checkout.session.async_payment_succeeded"]:
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

    def handle_payment_intent_succeeded(self, payment_intent):
        print("Payment succeeded (placeholder implementation)")
        # TODO: Implement payment success handling

    def handle_payment_intent_failed(self, payment_intent):
        print("Payment failed (placeholder implementation)")
        # TODO: Implement payment failure handling

    def handle_subscription_deleted(self, subscription):
        print("Subscription deleted (placeholder implementation)")
        # TODO: Implement subscription deletion handling


class PostHandler(BaseHTTPRequestHandler):
    def return_bad_request(self, error="Bad Request"):
        self.send_response(400)
        self.end_headers()
        self.wfile.write(error.encode("utf-8"))

    def return_ok(self, message="OK"):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def do_POST(self):
        if self.path == "/stripe-webhook":
            StripeWebhookHandler.do_POST(self)
        else:
            if self.headers.get("Content-Type") != "application/json":
                return self.return_bad_request()
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                print("Received JSON data:", data)
                self.handle_json(data)
            except ValueError as ex:
                return self.return_bad_request(str(ex))
            self.return_ok()

    def handle_json(self, data):
        if data.get("type") == "new-message":
            self.handle_new_message(data)
        else:
            print("Unhandled event type:", data.get("type"))

    def handle_new_message(self, data):
        # Extract basic message details
        chat_guid = data.get("data", {}).get("chats", [{}])[0].get("guid")
        message_text = data.get("data", {}).get("text", "")
        is_from_me = data.get("data", {}).get("isFromMe", False)
        sender = data.get("data", {}).get("handle", {}).get("address", "Unknown")
        message_guid = data.get("data", {}).get("guid")

        if is_from_me:
            return

        save_message(chat_guid, sender, message_text, message_guid)

        # If this is the first message in the conversation, send a welcome message
        if get_total_message_count(chat_guid) == 1:
            send_welcome_message(chat_guid)
            return

        # Process any attachments
        attachments = data.get("data", {}).get("attachments", [])
        file_path = process_attachments(attachments) if attachments else None

        # Generate response using LLM if there's text
        if message_text:
            response = generate_response(conversation_chain, message_text)
            print("Alfred response:", response)
            alfred_message_guid = send_text(chat_guid, response)
            if alfred_message_guid:
                save_message(chat_guid, "alfred@gtfol.inc", response, alfred_message_guid)
        else:
            print("No valid message to process.") 