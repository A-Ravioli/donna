import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Version information
SERVER_VERSION = "1.0.0"

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Server settings
SERVER_PORT = int(os.getenv("SERVER_PORT", 4321))
SERVER_HOST = os.getenv("SERVER_HOST", "")

# BlueBubbles configuration
BLUEBUBBLES_SERVER_ADDR = os.getenv("BLUEBUBBLES_SERVER_ADDR", "http://localhost:1234")
BLUEBUBBLES_SERVER_PASSWORD = os.getenv("BLUEBUBBLES_SERVER_PASSWORD", "")

# LLM configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # Can be 'openai', 'azure', 'anthropic', etc.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "")

# Anthropic settings (for Claude models)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Database paths
CONVERSATIONS_DB_PATH = BASE_DIR / "data" / "conversations.db"
USERS_DB_PATH = BASE_DIR / "data" / "users.db"

# Payment configuration
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")

# Email configuration  
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# Subscription codes
SECRET_SUBSCRIPTION_ACTIVATION_CODE = os.getenv("SECRET_SUBSCRIPTION_ACTIVATION_CODE", "")
SECRET_SUBSCRIPTION_DEACTIVATION_CODE = os.getenv("SECRET_SUBSCRIPTION_DEACTIVATION_CODE", "")

# System messages
WELCOME_MESSAGE = """
Hey! I'm Alfred, your personal COO. Here's what I can do for you:

- Manage tasks & schedule: Share your tasks, and I'll help prioritize and organize your schedule.
- Reminders: Set deadlines, and I'll remind you when needed.
- Integration: Google Calendar, Notion, and more.
- Ask me anything: I'm an AI you can text — I'm here 24/7 if you need anything.

Let's get started! What's the first thing you want to tackle today?
"""

PAYMENT_MESSAGE = (
    f"You've reached the maximum number of free messages. "
    f"To continue using me, please subscribe using this link: "
    f"{STRIPE_PAYMENT_LINK}"
)

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

# Composio MCP Integration
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "") 