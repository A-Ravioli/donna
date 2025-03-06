# Alfred platform integrations package

from .base import BaseIntegration, IntegrationRegistry
from .email import EmailIntegration
from .calendar import CalendarIntegration
from .transport import UberLyftIntegration
from .food import FoodDeliveryIntegration
from .messaging import SlackTeamsIntegration, DiscordIntegration

# Initialize the registry
registry = IntegrationRegistry()

# Register all integrations
registry.register(EmailIntegration())
registry.register(CalendarIntegration())
registry.register(UberLyftIntegration())
registry.register(FoodDeliveryIntegration())
registry.register(SlackTeamsIntegration())
registry.register(DiscordIntegration()) 