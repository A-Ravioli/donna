# Donna - Your Personal AI Assistant

Donna is a powerful and versatile AI assistant that helps you manage your digital life through text messaging.

## Features

- **Natural Language Processing**: Communicate with Donna naturally using everyday language
- **Memory System**: Donna remembers your preferences, previous conversations, and important details
- **Platform Integrations**: Connect with various services like email, calendar, ride-sharing, and food delivery
- **Subscription Management**: Handle subscriptions directly through text messaging
- **Intelligent Responses**: Context-aware responses that understand the nuances of your requests
- **Multi-Provider Support**: Use different LLM providers including OpenAI, Cerebras, and others

## Project Structure

The project follows a modular structure for better maintainability and scalability:

- **server.py**: Main entry point that initializes the server and handles HTTP requests
- **modules/**: Core modules of the application
  - **database.py**: Database operations and data persistence
  - **memory.py**: Memory system for remembering user information and conversations
  - **message_handler.py**: Processes incoming messages and generates responses
  - **utils.py**: Utility functions for common operations
  - **http_handlers.py**: Handles HTTP requests and webhook events
  - **subscription_manager.py**: Manages subscription commands and payments
  - **llm_providers.py**: Abstraction layer for different LLM providers
  - **integrations/**: Platform integration modules
    - **base.py**: Base classes for all integrations
    - **email.py**: Email integration (sending, reading, searching emails)
    - **calendar.py**: Calendar integration (scheduling, reminders)
    - **transport.py**: Ride-sharing integrations (Uber, Lyft)
    - **food.py**: Food delivery integrations (DoorDash, UberEats, Grubhub)
    - **messaging.py**: Messaging integrations (Slack, Teams, Discord)
    - **auth_utils.py**: Authentication utilities for integrations

## Memory System

Donna's memory system allows for:

- Creating conversation summaries to maintain context
- Remembering user preferences and settings
- Tracking important entities mentioned in conversations
- Analyzing sentiment to provide appropriate responses
- Storing integration usage data for personalized experiences

## Configuration

To configure Donna, create a `.env` file in the root directory with the following variables:

```
# BlueBubbles Server Configuration
BLUEBUBBLES_SERVER_PASSWORD=your-bluebubbles-server-password

# Default LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-3.5-turbo

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_ASSISTANT_ID=your-openai-assistant-id

# Stripe Configuration
STRIPE_API_KEY=your-stripe-api-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
STRIPE_PAYMENT_LINK=your-stripe-payment-link

# Resend Configuration
RESEND_API_KEY=your-resend-api-key

# Subscription Management
SECRET_SUBSCRIPTION_ACTIVATION_CODE=your-subscription-activation-code
SECRET_SUBSCRIPTION_DEACTIVATION_CODE=your-subscription-deactivation-code

# Additional configuration for integrations
# See .env.example for all available options
```

## Getting Started

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/donna.git
   cd donna
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration

4. Start the server:
   ```
   python src/server.py
   ```

## iMessage Integration

Donna integrates with iMessage through BlueBubbles, allowing you to use your Mac as a server. See [IMESSAGE_SETUP.md](docs/IMESSAGE_SETUP.md) for detailed setup instructions.

## Platform Integrations

Donna can integrate with various platforms to help manage your digital life. See the [INTEGRATIONS.md](docs/INTEGRATIONS.md) document for details on how to use each integration.

## LLM Providers

Donna supports multiple LLM providers, allowing you to choose based on your needs and preferences. See [LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) for configuration details and supported providers.

## Contributing

We welcome contributions to Donna! Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [OpenAI](https://openai.com/) for providing the AI capabilities
- [Stripe](https://stripe.com/) for payment processing
- [BlueBubbles](https://bluebubbles.app/) for iMessage integration
- [LangChain](https://langchain.com/) for the LLM abstraction layer
