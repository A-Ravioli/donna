# Setting Up Donna with iMessage

This guide will help you set up Donna to work with iMessage using your Mac as a server.

## Overview

Donna integrates with iMessage through [BlueBubbles](https://bluebubbles.app/), an open-source app that allows you to send and receive iMessages on non-Apple devices by setting up a server on your Mac. Donna receives messages from BlueBubbles and sends responses back through it.

## Requirements

- A Mac computer running macOS 10.15 Catalina or newer
- The Mac must stay on and connected to the internet while Donna is running
- A stable internet connection
- iMessage account set up and signed in on your Mac
- Python 3.8 or newer installed on your Mac

## Step 1: Set Up BlueBubbles Server

First, you need to install and configure the BlueBubbles server on your Mac:

1. Download the BlueBubbles server from [the official website](https://bluebubbles.app/downloads/)
2. Open the downloaded file and install the BlueBubbles server application
3. During setup, you'll be asked to:
   - Allow BlueBubbles the necessary permissions (Accessibility, Full Disk Access, Automation)
   - Create a server password (you'll need this for Donna configuration)
   - Configure your connection method (recommended: Private API)

4. Make sure the server is running and accessible from your local network

## Step 2: Configure BlueBubbles Server Settings

For Donna to receive messages:

1. Open the BlueBubbles server application
2. Go to "Server Settings" → "Advanced"
3. Enable "HTTP Callback URL"
4. Set the callback URL to: `http://localhost:4321/new_message`
5. Enable "Use Private API" if not already enabled
6. Save your settings

## Step 3: Configure Donna

1. Clone or download the Donna repository to your Mac
2. Navigate to the Donna directory and create a `.env` file in the `src` folder
3. Add the following to your `.env` file:
   ```
   BLUEBUBBLES_SERVER_PASSWORD=your-bluebubbles-server-password
   
   # LLM provider settings (using OpenAI as default)
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-openai-api-key
   OPENAI_ASSISTANT_ID=your-openai-assistant-id
   OPENAI_MODEL=gpt-3.5-turbo
   
   # Other optional settings for integrations
   ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Launch Donna

1. Start the Donna server:
   ```bash
   cd src
   python server.py
   ```

2. Verify that Donna is running successfully. You should see console output like:
   ```
   Threaded server started on port 4321
   Handling POST requests for messages and webhooks
   Handling GET requests for OAuth callbacks
   Loaded X platform integrations
   ```

## Step 5: Test the Integration

1. On your Mac, open the Messages app
2. Send a test message to yourself: "Hello Donna, are you there?"
3. If everything is set up correctly, Donna should receive the message via BlueBubbles and respond back through iMessage

## Troubleshooting

### Common Issues:

1. **BlueBubbles Server Connection Issues**
   - Make sure the BlueBubbles server is running
   - Check that your Mac hasn't gone to sleep
   - Verify the server password is correct in your `.env` file
   - Ensure the HTTP Callback URL is correctly set in BlueBubbles settings

2. **Message Not Being Processed**
   - Check the Donna console logs for errors
   - Verify that the Messages app on your Mac is working properly
   - Try restarting both the BlueBubbles server and Donna

3. **No Response from Donna**
   - Check if your OpenAI API key is valid
   - Verify the OPENAI_ASSISTANT_ID is correct
   - Look for error messages in the Donna console

### Viewing Logs

- Donna logs will appear in the terminal window where you started the server
- BlueBubbles server logs can be viewed from the BlueBubbles app under "View Logs"

## Running Donna Continuously

To keep Donna running in the background even after closing your terminal:

### Using `screen` (built into macOS)

1. Install `screen` if not already installed:
   ```bash
   brew install screen
   ```

2. Start a new screen session:
   ```bash
   screen -S donna
   ```

3. Navigate to your Donna directory and start the server:
   ```bash
   cd path/to/donna/src
   python server.py
   ```

4. Detach from the screen session by pressing `Ctrl+A` followed by `D`
5. To reattach to the session later:
   ```bash
   screen -r donna
   ```

### Using `nohup` (alternative method)

1. Navigate to your Donna directory
2. Use nohup to run the server in the background:
   ```bash
   cd path/to/donna/src
   nohup python server.py > donna.log 2>&1 &
   ```
3. The server will now run in the background, with output logged to `donna.log`

## Security Considerations

- BlueBubbles gives access to your iMessage account, so only install it on a trusted computer
- Keep your Mac secure and up to date
- Use a strong password for the BlueBubbles server
- Consider using a firewall to limit external connections to your Mac
- Regularly check the BlueBubbles access logs for suspicious activity

## Next Steps

Once you have Donna working with iMessage through BlueBubbles:

1. Try setting up [integrations](INTEGRATIONS.md) to expand Donna's capabilities
2. Explore different [LLM providers](LLM_PROVIDERS.md) for varied performance and cost options
3. Consider setting up automatic startup so Donna launches when your Mac boots

By following this guide, you should have a fully functional Donna assistant that works directly with your iMessages! 