import json
import sqlite3
import openai
from datetime import datetime, timezone
from .database import save_message, get_recent_messages, get_total_message_count

def save_memory(chat_guid, memory_type, content):
    """
    Save a memory entry for a specific chat
    memory_type can be: 'summary', 'key_info', 'user_preference', etc.
    
    Args:
        chat_guid (str): The chat GUID to save memory for
        memory_type (str): The type of memory
        content (str): The memory content
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO memory (chat_guid, memory_type, content) VALUES (?, ?, ?)",
        (chat_guid, memory_type, content),
    )
    conn.commit()
    conn.close()

def get_memories(chat_guid, memory_type=None, limit=10):
    """
    Retrieve memories for a specific chat, optionally filtered by memory_type
    
    Args:
        chat_guid (str): The chat GUID to get memories for
        memory_type (str, optional): The type of memory to filter by
        limit (int): Maximum number of memories to retrieve
        
    Returns:
        list: A list of (memory_type, content, timestamp) tuples
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    
    if memory_type:
        c.execute(
            "SELECT content, timestamp FROM memory WHERE chat_guid = ? AND memory_type = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_guid, memory_type, limit),
        )
    else:
        c.execute(
            "SELECT memory_type, content, timestamp FROM memory WHERE chat_guid = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_guid, limit),
        )
    
    result = c.fetchall()
    conn.close()
    return result

def get_conversation_history(chat_guid, limit=20):
    """
    Get conversation history formatted for use with language models
    
    Args:
        chat_guid (str): The chat GUID to get history for
        limit (int): Maximum number of messages to retrieve
        
    Returns:
        list: A list of formatted message dictionaries
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "SELECT sender, message, timestamp FROM messages WHERE chat_guid = ? ORDER BY timestamp DESC LIMIT ?",
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    
    # Format messages for LLM context (in reverse chronological order to get oldest first)
    formatted_messages = []
    for sender, message, timestamp in reversed(messages):
        if sender == "alfred@gtfol.inc":
            formatted_messages.append({"role": "assistant", "content": message})
        else:
            formatted_messages.append({"role": "user", "content": message})
    
    return formatted_messages

def create_conversation_summary(chat_guid):
    """
    Create a summary of the conversation using the OpenAI API
    
    Args:
        chat_guid (str): The chat GUID to summarize
        
    Returns:
        str: The summary, or None if an error occurred
    """
    conversation_history = get_conversation_history(chat_guid, limit=50)
    if not conversation_history:
        return None
    
    # Prepare the conversation for summarization
    prompt = "Summarize the key points from this conversation in a concise way that captures important user information, preferences, and context:\n\n"
    
    for msg in conversation_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['content']}\n"
    
    # Generate summary using OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations. Extract key information, user preferences, and important context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        summary = response.choices[0].message.content
        
        # Save the summary to memory
        save_memory(chat_guid, "summary", summary)
        return summary
    except Exception as e:
        print(f"Error creating conversation summary: {e}")
        return None

def clean_up_memories(chat_guid, max_memories=50):
    """
    Clean up memories for a chat to prevent excessive storage.
    Keeps the most recent memories and summaries.
    
    Args:
        chat_guid (str): The chat GUID
        max_memories (int): Maximum number of memories to keep per type
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    
    # Get memory types for this chat
    c.execute(
        "SELECT DISTINCT memory_type FROM memory WHERE chat_guid = ?",
        (chat_guid,)
    )
    memory_types = [row[0] for row in c.fetchall()]
    
    # For each memory type, keep only the most recent entries
    for memory_type in memory_types:
        # Keep summaries as they are more important (only delete old ones)
        if memory_type == "summary":
            # Delete all but the 5 most recent summaries
            c.execute(
                """
                DELETE FROM memory 
                WHERE chat_guid = ? AND memory_type = ? AND id NOT IN (
                    SELECT id FROM memory 
                    WHERE chat_guid = ? AND memory_type = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                )
                """,
                (chat_guid, memory_type, chat_guid, memory_type)
            )
        else:
            # For other memory types, keep the most recent entries
            c.execute(
                """
                DELETE FROM memory 
                WHERE chat_guid = ? AND memory_type = ? AND id NOT IN (
                    SELECT id FROM memory 
                    WHERE chat_guid = ? AND memory_type = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                )
                """,
                (chat_guid, memory_type, chat_guid, memory_type, max_memories // len(memory_types))
            )
    
    conn.commit()
    conn.close()
    print(f"Cleaned up memories for chat_guid: {chat_guid}")

def analyze_user_sentiment(chat_guid, message_text):
    """
    Analyze the sentiment of a user message and store it in memory.
    
    Args:
        chat_guid (str): The chat GUID for the conversation
        message_text (str): The message to analyze
    """
    try:
        # Skip short messages as they may not have clear sentiment
        if len(message_text) < 10:
            return
            
        sentiment_prompt = f"Analyze the sentiment in this message: '{message_text}'. Return ONLY a single JSON object with these keys: 'sentiment' (positive, negative, neutral), 'emotion' (specific emotion), 'intensity' (1-5 scale)."
        
        sentiment_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You analyze sentiment in text. Return ONLY a JSON object with the requested fields."},
                {"role": "user", "content": sentiment_prompt}
            ],
            max_tokens=100
        )
        
        sentiment_data = json.loads(sentiment_response.choices[0].message.content)
        
        # Store the sentiment analysis in memory
        save_memory(
            chat_guid, 
            "sentiment",
            json.dumps(sentiment_data)
        )
        
        # If strong negative sentiment detected, make a note of it
        if sentiment_data.get("sentiment") == "negative" and sentiment_data.get("intensity", 0) >= 4:
            save_memory(
                chat_guid,
                "important_note",
                f"User expressed strong negative emotion ({sentiment_data.get('emotion')}) on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}."
            )
            
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")

def extract_user_preferences(chat_guid, message):
    """
    Extract any user preferences from a message and store them in memory.
    
    Args:
        chat_guid (str): The chat GUID
        message (str): The message text to analyze
    """
    if not any(keyword in message.lower() for keyword in ["prefer", "like", "don't like", "hate", "love", "favorite"]):
        return
        
    try:
        # Extract preferences using OpenAI
        preference_prompt = f"Extract any user preferences from this message: '{message}'. If no preferences found, respond with 'None'."
        preference_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract user preferences from text. Be concise."},
                {"role": "user", "content": preference_prompt}
            ],
            max_tokens=100
        )
        preference = preference_response.choices[0].message.content
        
        if preference.lower() != "none":
            # Save the extracted preference
            save_memory(chat_guid, "user_preference", preference)
    except Exception as e:
        print(f"Error extracting user preferences: {e}")

def extract_entities(chat_guid, message_text):
    """
    Extract entities from a message and store them in memory.
    
    Args:
        chat_guid (str): The chat GUID
        message_text (str): The message to extract entities from
    """
    # Only do this extraction for longer messages to save API costs
    if len(message_text) <= 50:
        return
        
    try:
        entity_prompt = f"Extract any key entities or information from this message that should be remembered: '{message_text}'. Format as a JSON list of key-value pairs. If none, return empty list []."
        entity_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract structured information from text. Return ONLY a valid JSON array of key-value pairs."},
                {"role": "user", "content": entity_prompt}
            ],
            max_tokens=200
        )
        
        entities = json.loads(entity_response.choices[0].message.content)
        
        # Save extracted entities to memory
        if entities and isinstance(entities, list) and len(entities) > 0:
            for entity in entities:
                for key, value in entity.items():
                    save_memory(chat_guid, f"entity_{key}", value)
    except Exception as e:
        print(f"Error extracting entities: {e}") 