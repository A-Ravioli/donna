import os
from dotenv import load_dotenv

load_dotenv()

# Server configuration
SERVER_ADDR = "http://localhost:1234"
SERVER_PASSWORD = os.getenv("BLUEBUBBLES_SERVER_PASSWORD")

# Stripe configuration
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Message templates
WELCOME_MESSAGE = (
    "Hey! I'm Alfred, your personal COO. Here's what I can do for you:\n\n"
    "- Manage tasks & schedule: Share your tasks, and I'll help prioritize and organize your schedule.\n"
    "- Reminders: Set deadlines, and I'll remind you when needed.\n"
    "- Integration: Google Calendar, Notion, and more.\n"
    "- Ask me anything: I'm an AI you can text — I'm here 24/7 if you need anything.\n\n"
    "Let's get started! What's the first thing you want to tackle today?"
)

PAYMENT_MESSAGE = (
    "You've reached the maximum number of free messages. To continue using me, "
    "please subscribe using this link: " + STRIPE_PAYMENT_LINK
)

ACTIVATION_MESSAGE = (
    "Congratulations! Your subscription has been activated. "
    "You now have unlimited access to me. Enjoy!"
)

DEACTIVATION_MESSAGE = (
    "Your subscription has been deactivated. Please consider subscribing again to continue using me: " + STRIPE_PAYMENT_LINK
)

EXPIRED_MESSAGE = (
    "Your subscription has expired. To continue using me, please renew your subscription using: " + STRIPE_PAYMENT_LINK
)

SUBSCRIPTION_CANCELLATION_MESSAGE = (
    "Your subscription has been cancelled. To continue using me, please renew your subscription using: " + STRIPE_PAYMENT_LINK
) 