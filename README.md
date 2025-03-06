# iMessage AI Assistant with LangChain and Composio

An AI-powered iMessage assistant using BlueBubbles server integration, with LangChain for flexible LLM integration and Composio MCP for connecting to various productivity apps.

## Features

- **AI-Powered Messaging**: Receive and respond to iMessages with AI assistance
- **Multi-Modal Support**: Process text and images in conversations
- **LangChain Integration**: Swap between different AI models (OpenAI, Anthropic, etc.)
- **Composio MCP Integration**: Connect to Google Calendar, Notion, and other apps
- **Subscription Management**: Handle paid subscriptions through Stripe
- **Email Notifications**: Send activation/subscription emails through Resend

## Architecture

The application follows a modular architecture:

- **API**: HTTP request handlers for webhooks and external APIs
- **Config**: Configuration settings and environment variables
- **Database**: SQLite database management for conversations and users
- **Integrations**: External service integration (Composio, etc.)
- **Models**: LLM integration through LangChain
- **Services**: Messaging, email, and other core services
- **Utils**: Utility functions and helpers

## Prerequisites

- Python 3.9+
- BlueBubbles server (for iMessage integration)
- OpenAI API key (or other LLM provider API key)
- Composio API key (for app integrations)
- Stripe account (for subscription handling)
- Resend API key (for email notifications)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/imessage-assistant.git
cd imessage-assistant
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r src/requirements.txt
```

4. Copy the example environment file and fill in your keys:
```bash
cp src/.env.example src/.env
```

## Configuration

Edit `src/.env` with your API keys and configuration:

```
# BlueBubbles configuration
BLUEBUBBLES_SERVER_ADDR=http://localhost:1234
BLUEBUBBLES_SERVER_PASSWORD=your-bluebubbles-server-password

# LLM configuration
LLM_PROVIDER=openai  # or anthropic, etc.
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key  # Optional

# Server configuration
SERVER_HOST=
SERVER_PORT=4321

# Stripe configuration
STRIPE_API_KEY=your-stripe-api-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
STRIPE_PAYMENT_LINK=your-stripe-payment-link

# Email configuration
RESEND_API_KEY=your-resend-api-key

# Composio configuration
COMPOSIO_API_KEY=your-composio-api-key

# Subscription codes
SECRET_SUBSCRIPTION_ACTIVATION_CODE=your-activation-code
SECRET_SUBSCRIPTION_DEACTIVATION_CODE=your-deactivation-code
```

## Running the Server

Start the server with:

```bash
python src/server.py
```

The server will listen for webhook requests on the configured port (default 4321).

## Webhook Setup

1. **BlueBubbles Server**: Configure your BlueBubbles server to send webhooks to:
   - `http://your-server:4321/webhook/message`

2. **Stripe Webhooks**: In your Stripe Dashboard, set up a webhook to:
   - `http://your-server:4321/webhook/stripe`
   - Events to monitor: `payment_intent.succeeded`, `payment_intent.payment_failed`, `customer.subscription.deleted`

## Composio MCP Integration

The application integrates with Composio MCP to connect with various productivity apps:

1. Set up your Composio account and get your API key
2. Update the `COMPOSIO_API_KEY` in your `.env` file
3. Use the `ComposioClient` class to interact with external services

## Development

### Adding New Integrations

To add a new integration:

1. Create a new service in `src/services/`
2. Add any required API keys to `src/config/settings.py`
3. Update the `.env.example` file with the new variables
4. Implement the integration in the appropriate handler

### LLM Model Swapping

To use a different LLM:

1. Update the `LLM_PROVIDER` in your `.env` file
2. Add any additional API keys required by the provider
3. If adding a new provider, extend the `LLMManager` class in `src/models/llm_manager.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) - For the LLM framework
- [Composio](https://docs.composio.dev/) - For the MCP integration
- [BlueBubbles](https://bluebubbles.app/) - For the iMessage server integration
