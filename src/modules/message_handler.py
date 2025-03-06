import json
import openai
import os
from time import sleep
from datetime import datetime, timezone

from .database import save_message, get_total_message_count
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

# OpenAI API key and Alfred's assistant ID
openai.api_key = os.getenv("OPENAI_API_KEY")
alfred_assistant_id = os.getenv("ALFRED_ASSISTANT_ID")

# Stripe payment link
STRIPE_PAYMENT_LINK = os.getenv("STRIPE_PAYMENT_LINK")

# Welcome message for new users
WELCOME_MESSAGE = """Hello! 👋 I'm Alfred, your AI assistant.

I can help you with a variety of tasks such as:
• Answering questions
• Providing recommendations
• Assisting with research
• And much more!

Just let me know what you need help with, and I'll do my best to assist you."""

def process_message_with_alfred(chat_guid, message_text, data, is_first_message):
    """
    Processes a message with Alfred.

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

    print("Detected incoming message... Processing with Alfred...")

    # Extract any user preferences
    extract_user_preferences(chat_guid, message_text)

    # Create Alfred's response
    assistant_response = create_alfred_response(
        chat_guid, message_text, file_id, chat_guid.startswith("iMessage;+;")
    )

    print("Dispatching Alfred's response...")
    alfred_message_guid = send_text(chat_guid, assistant_response)
    if alfred_message_guid:
        # Only save the message if it's not the payment link response
        if STRIPE_PAYMENT_LINK not in assistant_response:
            save_message(
                chat_guid,
                "alfred@gtfol.inc",
                assistant_response,
                alfred_message_guid,
            )
            print("Response dispatched and saved")
        else:
            print("Payment request message sent")
    else:
        print("Failed to get message_guid for Alfred's response")
    
    # Clean up old memories periodically
    total_messages = get_total_message_count(chat_guid)
    if total_messages % 50 == 0:  # Clean up every 50 messages
        clean_up_memories(chat_guid)


def send_welcome_message(chat_guid):
    """
    Sends the welcome message to a new user.

    Args:
        chat_guid (str): The chat GUID to send the message to
    """
    # Share Alfred's contact card
    contact_card_shared = share_contact_card(chat_guid)
    if contact_card_shared:
        print(f"Contact card shared with chat_guid: {chat_guid}")
    else:
        print(f"Failed to share contact card with chat_guid: {chat_guid}")

    # Send welcome message
    alfred_message_guid = send_text(chat_guid, WELCOME_MESSAGE)
    if alfred_message_guid:
        save_message(
            chat_guid,
            "alfred@gtfol.inc",
            WELCOME_MESSAGE,
            alfred_message_guid,
        )
        print(f"Welcome message sent to chat_guid: {chat_guid}")
    else:
        print(f"Failed to send welcome message to chat_guid: {chat_guid}")


def process_attachments(attachments):
    """
    Processes attachments and uploads image to OpenAI if available.

    Args:
        attachments (list): List of attachment dictionaries

    Returns:
        str: OpenAI file ID or None
    """
    for attachment in attachments:
        if attachment.get("mimeType", "").startswith("image/"):
            try:
                # Download and process the attachment
                temp_file_path = download_and_process_attachment(attachment)
                if not temp_file_path:
                    continue

                # Upload the image to OpenAI
                with open(temp_file_path, "rb") as file:
                    openai_file = openai.files.create(file=file, purpose="vision")

                return openai_file.id
            except Exception as e:
                print(f"Error uploading file to OpenAI: {e}")
    return None


def create_alfred_response(chat_guid, message, file_id=None, is_group_chat=False):
    """
    Creates a response from Alfred using the OpenAI API.

    Args:
        chat_guid (str): The chat GUID for the conversation
        message (str): The message to process
        file_id (str): OpenAI file ID for the image, if available
        is_group_chat (bool): Whether this is a group chat

    Returns:
        str: Alfred's response
    """
    from .database import get_thread_id, save_thread_id, get_recent_messages
    
    try:
        # Check if there's an existing thread for this conversation
        thread_id = get_thread_id(chat_guid)
        if thread_id:
            thread = openai.beta.threads.retrieve(thread_id)
        else:
            thread = openai.beta.threads.create()
            save_thread_id(chat_guid, thread.id)

        # Create message content
        content = []
        
        # Fetch memory information for the user
        memories = get_memories(chat_guid)
        conversation_summary = None
        user_preferences = None
        sentiment_data = None
        important_notes = []
        entities = {}
        
        # Extract relevant memories
        for mem_type, mem_content, _ in memories:
            if mem_type == "summary":
                conversation_summary = mem_content
            elif mem_type == "user_preference":
                user_preferences = mem_content
            elif mem_type == "sentiment":
                try:
                    sentiment_data = json.loads(mem_content)
                except:
                    pass
            elif mem_type == "important_note":
                important_notes.append(mem_content)
            elif mem_type.startswith("entity_"):
                entity_key = mem_type.replace("entity_", "")
                entities[entity_key] = mem_content
        
        # Add memory context if available
        memory_context = ""
        if conversation_summary:
            memory_context += f"Previous conversation summary: {conversation_summary}\n\n"
        
        if user_preferences:
            memory_context += f"User preferences: {user_preferences}\n\n"
            
        if sentiment_data:
            memory_context += f"User's recent sentiment: {sentiment_data.get('sentiment', 'unknown')}, "
            memory_context += f"emotion: {sentiment_data.get('emotion', 'unknown')}, "
            memory_context += f"intensity: {sentiment_data.get('intensity', 'unknown')}\n\n"
        
        if important_notes:
            memory_context += "Important notes about this user:\n"
            for note in important_notes[:3]:  # Limit to 3 most recent notes
                memory_context += f"- {note}\n"
            memory_context += "\n"
            
        if entities:
            memory_context += "Known entities from previous conversations:\n"
            for key, value in entities.items():
                memory_context += f"- {key}: {value}\n"
            memory_context += "\n"
        
        # Get recent conversation history
        recent_messages = get_recent_messages(chat_guid, 5)
        conversation_context = ""
        
        if recent_messages:
            conversation_context = "Recent conversation:\n"
            for sender, msg in recent_messages:
                # Format the sender name to be more readable
                display_name = "You" if sender == "alfred@gtfol.inc" else "User"
                conversation_context += f"{display_name}: {msg}\n"
        
        # Create a complete context combining memory and recent messages
        complete_context = ""
        if memory_context or conversation_context:
            complete_context = "CONTEXT (not visible to user):\n"
            if memory_context:
                complete_context += memory_context
            if conversation_context:
                complete_context += conversation_context
            complete_context += "\nEnd of context. Use this information to provide a more personalized response. Adjust your tone based on the user's sentiment if available.\n\n"
            
            # Add context to the message content
            content.append({"type": "text", "text": complete_context})

        # If it's a group chat, include additional recent messages for context
        if is_group_chat:
            group_recent_messages = get_recent_messages(chat_guid, 15)
            if group_recent_messages:
                group_context = "Here are the recent messages in the group chat:\n\n"
                for sender, msg in group_recent_messages:
                    group_context += f"{sender}: {msg}\n"
                group_context += "\nPlease consider this context when responding to the following message:\n"
                content.append({"type": "text", "text": group_context})

        if message:
            content.append({"type": "text", "text": message})
        elif file_id:
            content.append(
                {
                    "type": "text",
                    "text": "Please look at this image and provide your thoughts on it.",
                }
            )

        if file_id:
            content.append(
                {"type": "image_file", "image_file": {"file_id": file_id}}
            )

        # Create the message in the thread
        openai.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=content
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=alfred_assistant_id
        )

        # Wait for the run to complete
        while run.status != "completed":
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            sleep(1)

        # Retrieve Alfred's response
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        alfred_response = messages.data[0].content[0].text.value
        
        # Update conversation summary periodically 
        # (e.g., every 10 messages or when certain keywords are detected)
        total_messages = get_total_message_count(chat_guid)
        if total_messages % 10 == 0:  # Create a summary every 10 messages
            create_conversation_summary(chat_guid)

        return alfred_response
    except Exception as e:
        print(f"❌ Error processing message with Alfred: {e}")
        return "I'm sorry, I encountered an error while processing your message." 