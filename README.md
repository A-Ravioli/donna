# Alfred - AI Assistant with Memory

Alfred is an AI assistant that can communicate through iMessage using the BlueBubbles service. It features a sophisticated memory system that allows it to remember important information, user preferences, and conversational context.

## Project Structure

The codebase is organized into the following files and directories:

```
src/
  ├─ server_new.py       # Main entry point for the server
  ├─ server.py           # Legacy server file (to be replaced by server_new.py)
  └─ modules/
      ├─ __init__.py     # Package initialization
      ├─ database.py     # Database operations
      ├─ memory.py       # Memory management
      ├─ message_handler.py # Message processing and responses
      ├─ utils.py        # Utility functions
      └─ http_handlers.py # HTTP request handlers
```

## Memory System

Alfred's memory system is designed to enhance the conversational experience by:

1. **Remembering User Information**: Alfred extracts and stores important entities mentioned by users.
2. **Tracking Preferences**: Alfred identifies and remembers user preferences.
3. **Conversation Summaries**: Periodically creates summaries of conversations to maintain context.
4. **Sentiment Analysis**: Analyzes user emotions to adjust response tone appropriately.
5. **Contextual Responses**: Uses previous interactions to provide personalized responses.

## Configuration

The system uses environment variables for configuration. Create a `.env` file in the root directory with:

```
BLUEBUBBLES_SERVER_PASSWORD=your_password
OPENAI_API_KEY=your_openai_api_key
ALFRED_ASSISTANT_ID=your_assistant_id
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret
STRIPE_PAYMENT_LINK=your_payment_link
RESEND_API_KEY=your_resend_api_key
```

## Getting Started

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables as described above.

3. Run the server:
   ```
   python src/server_new.py
   ```

## Migrating from the Old Server

The new server structure is designed to be a drop-in replacement for the old server. After testing, you can replace the old server with the new one:

```
mv src/server.py src/server_old.py
mv src/server_new.py src/server.py
```

## Contributing

To add new features or modify existing ones, please follow the established code structure:

1. Database operations go in `modules/database.py`
2. Memory-related functions go in `modules/memory.py`
3. Message handling goes in `modules/message_handler.py`
4. Utility functions go in `modules/utils.py`
5. HTTP request handlers go in `modules/http_handlers.py`
