import json
import stripe
import os
from datetime import datetime, timezone
import re

from .database import save_user_subscription, check_subscription_status
from .utils import send_text, send_activation_email
from .memory import save_memory

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Subscription commands
SUBSCRIPTION_COMMANDS = [
    "subscribe", 
    "unsubscribe", 
    "cancel", 
    "subscription status", 
    "upgrade", 
    "downgrade"
]

# Subscription plans - customize based on your pricing structure
SUBSCRIPTION_PLANS = {
    "basic": {
        "price": "$4.99/month",
        "description": "Basic plan with limited features",
        "payment_link": os.getenv("STRIPE_BASIC_PAYMENT_LINK", STRIPE_PAYMENT_LINK)
    },
    "premium": {
        "price": "$9.99/month",
        "description": "Premium plan with full features",
        "payment_link": os.getenv("STRIPE_PREMIUM_PAYMENT_LINK", STRIPE_PAYMENT_LINK)
    }
}

def is_subscription_command(message_text):
    """
    Check if a message is a subscription-related command.
    
    Args:
        message_text (str): The message text
        
    Returns:
        bool: True if this is a subscription command
    """
    message_lower = message_text.lower()
    
    for cmd in SUBSCRIPTION_COMMANDS:
        if cmd in message_lower:
            return True
            
    return False

def extract_subscription_info(message_text):
    """
    Extract subscription information from a message.
    
    Args:
        message_text (str): The message text
        
    Returns:
        dict: Extracted information including command and plan
    """
    message_lower = message_text.lower()
    
    # Identify command
    command = None
    for cmd in SUBSCRIPTION_COMMANDS:
        if cmd in message_lower:
            command = cmd
            break
    
    # Identify plan
    plan = None
    if "basic" in message_lower:
        plan = "basic"
    elif "premium" in message_lower or "full" in message_lower:
        plan = "premium"
    
    # Extract email if present
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message_text)
    email = email_match.group(0) if email_match else None
    
    # Extract name if present
    name = None
    name_patterns = [
        r'my name is (\w+)',
        r'name:? (\w+)',
        r'i am (\w+)'
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, message_lower)
        if name_match:
            name = name_match.group(1).capitalize()
            break
    
    return {
        "command": command,
        "plan": plan,
        "email": email,
        "name": name
    }

def handle_subscription_command(chat_guid, message_text, sender):
    """
    Handle a subscription-related command.
    
    Args:
        chat_guid (str): The chat GUID
        message_text (str): The message text
        sender (str): The sender identifier
        
    Returns:
        tuple: Response message and any payment link to send
    """
    sub_info = extract_subscription_info(message_text)
    command = sub_info.get("command")
    plan = sub_info.get("plan", "premium")  # Default to premium if not specified
    email = sub_info.get("email")
    
    # If email not provided in message, try to use sender
    if not email and "@" in sender:
        email = sender
    
    # Check current subscription status
    current_status = check_subscription_status(email=email)
    
    if "subscribe" == command or "upgrade" == command:
        # Handle subscription request
        if current_status == "active":
            return "You already have an active subscription. Thank you for your continued support!", None
        
        # Include plan details in the response
        plan_details = SUBSCRIPTION_PLANS.get(plan, SUBSCRIPTION_PLANS["premium"])
        
        response = f"Thanks for your interest in subscribing to donna! The {plan} plan costs {plan_details['price']} and includes {plan_details['description']}.\n\nTo complete your subscription, please click the link I'm about to send. If you provided an email, you'll receive a confirmation once your subscription is active."
        
        # Save information to memory
        save_memory(chat_guid, "subscription_intent", json.dumps({
            "plan": plan,
            "email": email,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }))
        
        return response, plan_details["payment_link"]
    
    elif "unsubscribe" == command or "cancel" == command:
        # Handle unsubscribe request
        if current_status != "active":
            return "You don't currently have an active subscription.", None
        
        # In a real system, you would connect to Stripe's API here to cancel the subscription
        # For now, we'll just update our database
        save_user_subscription("cancelled", email=email)
        
        response = "I've processed your cancellation request. Your subscription will remain active until the end of your current billing period. You'll receive a confirmation email shortly."
        
        # Send an email confirmation (still useful even with text-based management)
        # We would need additional code here to look up the user's name from our database
        
        return response, None
    
    elif "subscription status" in command:
        # Handle status check
        if current_status == "active":
            return "You have an active subscription. Thank you for your support!", None
        elif current_status == "cancelled":
            return "Your subscription has been cancelled and will expire at the end of your current billing period.", None
        else:
            plan_details = SUBSCRIPTION_PLANS.get("premium")
            return "You don't currently have an active subscription. Would you like to subscribe for " + plan_details["price"] + " per month?", None
    
    return "I didn't understand your subscription request. You can say 'subscribe', 'unsubscribe', or 'check subscription status'.", None

def process_payment_confirmation(customer_id, subscription_id=None, plan="premium"):
    """
    Process a successful payment confirmation from Stripe.
    
    Args:
        customer_id (str): Stripe customer ID
        subscription_id (str): Stripe subscription ID
        plan (str): The subscription plan
        
    Returns:
        bool: True if successful
    """
    try:
        # Retrieve customer information from Stripe
        customer = stripe.Customer.retrieve(customer_id)
        phone_number = customer.phone
        email = customer.email
        name = customer.name
        
        # Save subscription in the database
        save_user_subscription(
            status="active", 
            phone_number=phone_number, 
            email=email
        )
        
        # Also store subscription info in our user database (we'd need to add this)
        # store_user_subscription_details(email, subscription_id, plan)
        
        # Send confirmation email
        send_activation_email(email, name)
        
        # Send confirmation text if we have a phone number
        # (This would require finding the chat_guid associated with this phone number)
        # if phone_number:
        #     chat_guid = find_chat_guid_by_phone(phone_number)
        #     if chat_guid:
        #         send_text(chat_guid, "Your subscription is now active! Thank you for subscribing to donna.")
        
        return True
    except Exception as e:
        print(f"Error processing payment confirmation: {e}")
        return False 