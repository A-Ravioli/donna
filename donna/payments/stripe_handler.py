import stripe
from donna.config import STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET
from donna.database.models import save_user_subscription, find_latest_chat_guid
from donna.messaging.bluebubbles import send_text
from donna.emails.sender import send_activation_email, send_failed_cancellation_email
from donna.config import ACTIVATION_MESSAGE, SUBSCRIPTION_CANCELLATION_MESSAGE

# Initialize the Stripe client
stripe.api_key = STRIPE_API_KEY

def handle_payment_intent_succeeded(payment_intent):
    """
    Handles a successful payment intent from Stripe.

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


def handle_payment_intent_failed(payment_intent):
    """
    Handles a failed payment intent from Stripe.

    Args:
        payment_intent (dict): The payment intent data
    """
    try:
        # Extract user information from the payment intent
        customer = stripe.Customer.retrieve(payment_intent["customer"])
        print(f"💳 Payment failed for customer: {customer}")
    except Exception as e:
        print(f"Error handling failed payment intent: {e}")


def handle_subscription_deleted(subscription):
    """
    Handles a deleted subscription from Stripe.

    Args:
        subscription (dict): The subscription data
    """
    try:
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
            # Send subscription cancellation message
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
            send_failed_cancellation_email(name, email, phone_number)
        else:
            print(f"💳 No chat_guid or email found for customer: {customer}")

        print(f"Subscription deleted: {subscription}")
    except Exception as e:
        print(f"Error handling subscription deletion: {e}")


def verify_stripe_signature(payload, sig_header):
    """
    Verifies the Stripe signature on a webhook event.

    Args:
        payload (str): The raw payload from the webhook
        sig_header (str): The Stripe-Signature header

    Returns:
        dict: The verified event or None if verification fails
    """
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        print("Invalid payload")
        return None
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        print("Invalid signature")
        return None 