# donna

The assistant you wish you had

## Overview

Donna is a sophisticated assistant that integrates with messaging systems to provide AI-powered responses, task management, and more. This project uses the BlueBubbles API to connect with iMessage and provides a customizable AI assistant experience.

## Features

- AI-powered conversation through OpenAI's Assistant API
- iMessage integration via BlueBubbles
- Subscription management with Stripe
- Email notifications via Resend
- Image recognition and processing capabilities
- Group chat support

## Setup

1. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the root directory with the following variables:
   ```
   # BlueBubbles server
   BLUEBUBBLES_SERVER_PASSWORD="your_bluebubbles_password"

   # OpenAI
   OPENAI_API_KEY="your_openai_api_key"
   ALFRED_ASSISTANT_ID="your_openai_assistant_id"

   # Stripe
   STRIPE_API_KEY="your_stripe_api_key"
   STRIPE_WEBHOOK_SECRET="your_stripe_webhook_secret"
   STRIPE_PAYMENT_LINK="your_stripe_payment_link"

   # Resend
   RESEND_API_KEY="your_resend_api_key"

   # Secret codes
   SECRET_SUBSCRIPTION_ACTIVATION_CODE="your_activation_code"
   SECRET_SUBSCRIPTION_DEACTIVATION_CODE="your_deactivation_code"
   ```

3. Start the server:
   ```
   python main.py
   ```

## Project Structure

The project is organized into several modules:

- `donna/config.py` - Configuration and environment variables
- `donna/database/` - Database operations
- `donna/messaging/` - BlueBubbles messaging API integration
- `donna/assistant/` - OpenAI assistant integration
- `donna/payments/` - Stripe payment processing
- `donna/emails/` - Email sending functionality
- `donna/server/` - HTTP server and request handling
- `main.py` - Main entry point

## Usage

1. Configure your BlueBubbles server to send webhooks to your server at `http://your-server:4321`
2. Configure Stripe to send webhooks to `http://your-server:4321/stripe-webhook`
3. Start conversations with the assistant via iMessage

## License

MIT