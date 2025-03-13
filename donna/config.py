import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# BlueBubbles server address and password
SERVER_ADDR = "http://localhost:1234"
SERVER_PASSWORD = os.getenv("BLUEBUBBLES_SERVER_PASSWORD")

# OpenAI API key and Alfred's assistant ID
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALFRED_ASSISTANT_ID = os.getenv("ALFRED_ASSISTANT_ID")

# Stripe configuration
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Resend configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Secret codes
SECRET_SUBSCRIPTION_ACTIVATION_CODE = os.getenv("SECRET_SUBSCRIPTION_ACTIVATION_CODE")
SECRET_SUBSCRIPTION_DEACTIVATION_CODE = os.getenv("SECRET_SUBSCRIPTION_DEACTIVATION_CODE")

# Common messages
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