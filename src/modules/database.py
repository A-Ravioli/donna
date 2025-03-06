import sqlite3
from datetime import datetime, timezone

def init_db():
    """
    Initialize the database and create necessary tables if they don't exist.
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            chat_guid TEXT,
            sender TEXT,
            message TEXT,
            message_guid TEXT UNIQUE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            chat_guid TEXT PRIMARY KEY,
            thread_id TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            status TEXT,
            phone_number TEXT,
            email TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Create memory table for storing conversation summaries and key information
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY,
            chat_guid TEXT,
            memory_type TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

def init_users_db():
    """
    Initialize the users database and create necessary tables if they don't exist.
    """
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            phone_number TEXT UNIQUE,
            email TEXT UNIQUE,
            name TEXT,
            status TEXT,
            subscription_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

def get_thread_id(chat_guid):
    """
    Get the thread ID for a chat GUID.
    
    Args:
        chat_guid (str): The chat GUID to get the thread ID for
        
    Returns:
        str: The thread ID, or None if not found
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute("SELECT thread_id FROM threads WHERE chat_guid = ?", (chat_guid,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def save_thread_id(chat_guid, thread_id):
    """
    Save a thread ID for a chat GUID.
    
    Args:
        chat_guid (str): The chat GUID to save the thread ID for
        thread_id (str): The thread ID to save
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO threads (chat_guid, thread_id) VALUES (?, ?)",
        (chat_guid, thread_id),
    )
    conn.commit()
    conn.close()

def save_message(chat_guid, sender, message, message_guid):
    """
    Save a message to the database.
    
    Args:
        chat_guid (str): The chat GUID the message is from
        sender (str): The sender of the message
        message (str): The message content
        message_guid (str): The message GUID
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO messages (chat_guid, sender, message, message_guid) VALUES (?, ?, ?, ?)",
        (chat_guid, sender, message, message_guid),
    )
    conn.commit()
    conn.close()

def get_recent_messages(chat_guid, limit=10):
    """
    Get the most recent messages for a chat GUID.
    
    Args:
        chat_guid (str): The chat GUID to get messages for
        limit (int): Maximum number of messages to retrieve
        
    Returns:
        list: A list of (sender, message) tuples
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "SELECT sender, message FROM messages WHERE chat_guid = ? ORDER BY timestamp DESC LIMIT ?",
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    return messages

def get_message_by_guid(message_guid):
    """
    Get a message by its GUID.
    
    Args:
        message_guid (str): The message GUID to look up
        
    Returns:
        tuple: A (chat_guid, sender, message) tuple, or None if not found
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "SELECT chat_guid, sender, message FROM messages WHERE message_guid = ?",
        (message_guid,),
    )
    result = c.fetchone()
    conn.close()
    return result

def get_total_message_count(chat_guid):
    """
    Get the total number of messages for a chat GUID.
    
    Args:
        chat_guid (str): The chat GUID to count messages for
        
    Returns:
        int: The number of messages
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE chat_guid = ?", (chat_guid,))
    count = c.fetchone()[0]
    conn.close()
    return count

def save_user_subscription(status, phone_number=None, email=None):
    """
    Save a user's subscription status.
    
    Args:
        status (str): The subscription status
        phone_number (str, optional): The user's phone number
        email (str, optional): The user's email address
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO subscriptions (status, phone_number, email) VALUES (?, ?, ?)",
        (status, phone_number, email),
    )
    conn.commit()
    conn.close()

def find_latest_chat_guid(identifier):
    """
    Find the most recent chat GUID for a phone number or email.
    
    Args:
        identifier (str): Phone number or email to look for
        
    Returns:
        str: The most recent chat GUID, or None if not found
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    
    # Try to find a match in the sender field
    c.execute(
        """
        SELECT chat_guid FROM messages 
        WHERE sender LIKE ? OR sender LIKE ? 
        ORDER BY timestamp DESC LIMIT 1
        """,
        (f"%{identifier}%", f"%{identifier}%"),
    )
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None

def check_subscription_status(phone_number=None, email=None):
    """
    Check a user's subscription status.
    
    Args:
        phone_number (str, optional): The user's phone number
        email (str, optional): The user's email address
        
    Returns:
        str: The subscription status, or None if not found
    """
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    
    if phone_number:
        c.execute(
            "SELECT status FROM subscriptions WHERE phone_number = ? ORDER BY timestamp DESC LIMIT 1",
            (phone_number,),
        )
    elif email:
        c.execute(
            "SELECT status FROM subscriptions WHERE email = ? ORDER BY timestamp DESC LIMIT 1",
            (email,),
        )
    else:
        conn.close()
        return None
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None 