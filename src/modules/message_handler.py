import json
import openai
import os
from time import sleep
from datetime import datetime, timezone

from .database import save_message, get_total_message_count, get_thread_id, save_thread_id
from .memory import (
    get_memories,
    create_conversation_summary,
    analyze_user_sentiment,
    extract_user_preferences,
    extract_entities,
    clean_up_memories,
    save_memory
)
from .utils import send_text, share_contact_card, download_and_process_attachment
from .integrations import registry as integration_registry
from .llm_providers import get_model_provider, default_provider

# Get the LLM provider from environment or use default
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
model_provider = get_model_provider(LLM_PROVIDER)

# For backward compatibility with direct OpenAI calls elsewhere in the code
openai.api_key = os.getenv("OPENAI_API_KEY")
donna_assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

# Get the payment link from the environment
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK", "")

# Welcome message for new users
WELCOME_MESSAGE = """
Hello! I'm Donna, your personal AI assistant. I can help with various tasks:

• Answer questions and provide information
• Assist with scheduling and reminders
• Help with online shopping and orders
• Send messages to your contacts
• And much more!

How can I help you today?
"""

def process_message_with_donna(chat_guid, message_text, data, is_first_message):
    """
    Processes a message with Donna.

    Args:
        chat_guid (str): The chat GUID for the conversation
        message_text (str): The message to process
        data (dict): The data
        is_first_message (bool): Whether this is the first message
    """
    if is_first_message:
        send_welcome_message(chat_guid)
        # Initialize memory for new user
        initial_summary = f"New conversation started on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}."
        save_memory(chat_guid, "summary", initial_summary)
        return

    # Check if this message can be handled by one of our integrations
    sender = data.get("data", {}).get("handle", {}).get("address", "unknown")
    integration_response = check_integrations(chat_guid, message_text, sender)
    if integration_response:
        # Message was handled by an integration, send the response
        print(f"Message handled by integration: {integration_response[:50]}...")
        donna_message_guid = send_text(chat_guid, integration_response)
        if donna_message_guid:
            save_message(
                chat_guid,
                "donna@gtfol.inc",
                integration_response,
                donna_message_guid,
            )
            print("Integration response dispatched and saved")
        return

    # Analyze user sentiment (for messages longer than 10 characters)
    if len(message_text) >= 10:
        analyze_user_sentiment(chat_guid, message_text)

    # Extract entities from the message
    extract_entities(chat_guid, message_text)
    
    # Process any attachments
    attachments = data.get("data", {}).get("attachments", [])
    file_id = None
    if attachments:
        file_id = process_attachments(attachments)

    print("Detected incoming message... Processing with Donna...")

    # Extract any user preferences
    extract_user_preferences(chat_guid, message_text)

    # Create Donna's response
    assistant_response = create_donna_response(
        chat_guid, message_text, file_id, chat_guid.startswith("iMessage;+;")
    )

    print("Dispatching Donna's response...")
    donna_message_guid = send_text(chat_guid, assistant_response)
    if donna_message_guid:
        # Only save the message if it's not the payment link response
        if STRIPE_PAYMENT_LINK not in assistant_response:
            save_message(
                chat_guid,
                "donna@gtfol.inc",
                assistant_response,
                donna_message_guid,
            )
            print("Response dispatched and saved")
        else:
            print("Payment request message sent")
    else:
        print("Failed to get message_guid for Donna's response")
    
    # Clean up old memories periodically
    total_messages = get_total_message_count(chat_guid)
    if total_messages % 50 == 0:  # Clean up every 50 messages
        clean_up_memories(chat_guid)


def send_welcome_message(chat_guid):
    """
    Send a welcome message to a new user.
    
    Args:
        chat_guid (str): The chat GUID to send the welcome message to
    """
    print("New conversation detected. Sending welcome message...")
    welcome_guid = send_text(chat_guid, WELCOME_MESSAGE)
    if welcome_guid:
        save_message(chat_guid, "donna@gtfol.inc", WELCOME_MESSAGE, welcome_guid)
        print("Welcome message sent")
    else:
        print("Failed to get message_guid for welcome message")


def process_attachments(attachments):
    """
    Process any attachments in the message.
    
    Args:
        attachments (list): List of attachment objects
        
    Returns:
        str: File ID if an attachment was processed, None otherwise
    """
    if not attachments:
        return None
    
    for attachment in attachments:
        print(f"Processing attachment: {attachment}")
        file_path = download_and_process_attachment(attachment)
        if file_path:
            # For now, we just return the file path as the ID
            return file_path
    
    return None


def create_donna_response(chat_guid, message, file_id=None, is_group_chat=False):
    """
    Create a response using Donna.
    
    Args:
        chat_guid (str): The chat GUID
        message (str): The user message
        file_id (str, optional): The file ID of any attachment
        is_group_chat (bool, optional): Whether this is a group chat
        
    Returns:
        str: Donna's response
    """
    try:
        # Get memories for context
        memories = get_memories(chat_guid)
        
        # Create or get thread for this chat
        thread_id = get_thread_id(chat_guid)
        if not thread_id:
            thread_id = model_provider.create_thread()
            save_thread_id(chat_guid, thread_id)
        
        # Add the user message to the thread
        model_provider.add_message_to_thread(thread_id, message)
        
        # Prepare additional context from memories
        additional_instructions = "Use the following information in your response if relevant:"
        
        # Add memories to instructions if available
        if memories:
            for memory in memories:
                memory_type = memory["memory_type"]
                content = memory["content"]
                if memory_type == "summary":
                    additional_instructions += f"\nConversation summary: {content}"
                elif memory_type == "user_preference":
                    additional_instructions += f"\nUser preference: {content}"
                elif memory_type == "key_info":
                    additional_instructions += f"\nKey information: {content}"
                elif memory_type == "entity":
                    additional_instructions += f"\nRelevant entity: {content}"
                elif memory_type == "sentiment":
                    additional_instructions += f"\nUser sentiment: {content}"
                elif memory_type == "integration_usage":
                    additional_instructions += f"\nPrevious integration usage: {content}"
        
        # Add instructions for group chat if applicable
        if is_group_chat:
            additional_instructions += "\nThis is a group chat. Keep your responses concise and clearly addressed to the person who messaged you."
        
        # Run the thread with the additional context
        response_text = model_provider.run_thread(thread_id, additional_instructions)
        
        # Create a conversation summary every 10 messages
        total_messages = get_total_message_count(chat_guid)
        if total_messages % 10 == 0:
            create_conversation_summary(chat_guid)
        
        return response_text
    
    except Exception as e:
        print(f"❌ Error processing message with Donna: {e}")
        return "I'm sorry, I encountered an error while processing your message." 


def check_integrations(chat_guid, message_text, user_id):
    """
    Check if a message can be handled by one of our platform integrations.
    
    Args:
        chat_guid (str): The chat GUID
        message_text (str): The message text
        user_id (str): The user ID (typically email or phone number)
        
    Returns:
        str: The integration response if handled, None otherwise
    """
    # Check if any integration can handle this message
    integration = integration_registry.find_integration_for_message(message_text)
    
    if integration:
        print(f"Found integration that can handle message: {integration.get_name()}")
        try:
            # Process the message with the integration
            response = integration.process(user_id, message_text)
            
            # Add memory of this integration interaction
            save_memory(
                chat_guid,
                "integration_usage",
                f"Used {integration.get_name()} integration: {message_text[:100]}..."
            )
            
            return response
        except Exception as e:
            print(f"Error processing message with integration {integration.get_name()}: {e}")
            # Return a graceful error message
            return f"I tried to process your request with {integration.get_name()}, but encountered an error. Please try again or provide more details."
    
    return None 