# Donna Integrations

This document provides information on how to use the platform integrations available in Donna.

## Available Integrations

Donna can integrate with various services to help manage your digital life:

1. **Email Integration**: Send, read, and manage emails.
2. **Calendar Integration**: Schedule events, check your calendar, and manage appointments.
3. **Transport Integration (Uber/Lyft)**: Book rides, check ride status, and manage ride settings.
4. **Food Delivery Integration**: Order food, track deliveries, and save favorite restaurants.
5. **Messaging Integration (Slack/Teams)**: Send messages, check notifications, and manage channels.
6. **Discord Integration**: Send messages, check notifications, and manage Discord servers.

## How to Use Integrations

### Setting Up Integrations

Before you can use an integration, you need to set it up. Send a message to Donna with:

```
setup [integration name]
```

For example: `setup email`, `setup uber`, or `setup slack`.

Donna will guide you through the setup process, which typically involves:

1. Authentication via OAuth (you'll receive a link to authorize the integration)
2. Providing necessary account information
3. Setting preferences for that integration

### Email Integration Commands

- `setup email` - Configure your email settings
- `send email to [recipient] about [subject]` - Start composing an email
- `check my emails` - See recent emails
- `read email from [sender]` - Read emails from a specific sender
- `search emails for [term]` - Search your emails

### Calendar Integration Commands

- `setup calendar` - Configure your calendar settings
- `what's on my calendar today` - Check today's events
- `schedule a meeting with [person] on [date] at [time]` - Create a calendar event
- `cancel my meeting with [person]` - Cancel a meeting
- `reschedule [event] to [new date/time]` - Reschedule an event

### Transport Integration Commands (Uber/Lyft)

- `setup uber` or `setup lyft` - Configure your ride-sharing preferences
- `get me a ride to [destination]` - Request a ride
- `book an uber/lyft to [destination]` - Book a specific service
- `check my ride status` - Check the status of your current ride
- `cancel my ride` - Cancel your current ride
- `set my home address to [address]` - Update your home address

### Food Delivery Integration Commands

- `setup food delivery` - Configure your food delivery preferences
- `order food from [restaurant]` - Start ordering food
- `add [item] to my order` - Add items to your order
- `place my order` - Finalize and place your food order
- `check my order status` - Check the status of your current order
- `cancel my order` - Cancel your current order
- `save [restaurant] as favorite` - Save a restaurant to your favorites

### Messaging Integration Commands (Slack/Teams)

- `setup slack` or `setup teams` - Configure your messaging platform
- `send a message to [channel/person] on slack: [message]` - Send a message
- `check my slack notifications` - Check recent notifications
- `reply to [person] on slack: [message]` - Reply to a message
- `set my slack status to [status]` - Update your status

### Discord Integration Commands

- `setup discord` - Configure your Discord integration
- `send a message to [channel] on discord: [message]` - Send a Discord message
- `check my discord notifications` - Check recent Discord notifications
- `join [voice channel]` - Join a voice channel
- `leave voice chat` - Leave the current voice channel

## Troubleshooting

If you encounter issues with integrations:

1. Try using the `setup [integration] again` command to reconfigure the integration
2. Check that you have authorized the necessary permissions
3. Ensure your account details are correct
4. For OAuth-based integrations, you may need to reauthorize periodically

## Privacy and Security

Donna takes your privacy and security seriously:

- OAuth tokens are stored securely and encrypted
- Credentials are never shared with third parties
- You can revoke access at any time with `disconnect [integration]`
- All API calls are made over secure HTTPS connections

## Limitations

Some integrations may have limitations:

- Email and calendar integrations require OAuth authorization and will expire after a period
- Transport and food delivery integrations may not be available in all regions
- Message sending capabilities depend on the platform's API limitations
- Some advanced features may require premium subscription

## Future Integrations

We're continuously working to add new integrations. If you have suggestions for services you'd like to see integrated with Donna, let us know by sending a message: `suggest integration: [your idea]`. 