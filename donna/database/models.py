import sqlite3
from datetime import datetime, timezone

def init_db():
    """Initialize the conversations database."""
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS conversations
                 (chat_guid TEXT PRIMARY KEY, thread_id TEXT, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_guid TEXT,
                  sender TEXT,
                  message TEXT,
                  message_guid TEXT UNIQUE,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (chat_guid) REFERENCES conversations(chat_guid))"""
    )
    conn.commit()
    conn.close()


def init_users_db():
    """Initialize the users database."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS subscriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT UNIQUE,
                  email TEXT,
                  status TEXT,
                  subscription_date TIMESTAMP)"""
    )
    conn.commit()
    conn.close()


def get_thread_id(chat_guid):
    """Get a thread ID from the database.
    
    Args:
        chat_guid (str): The chat GUID to look up
        
    Returns:
        str: The thread ID or None if not found
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("SELECT thread_id FROM conversations WHERE chat_guid = ?", (chat_guid,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def save_thread_id(chat_guid, thread_id):
    """Save a thread ID to the database.
    
    Args:
        chat_guid (str): The chat GUID
        thread_id (str): The thread ID to save
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO conversations (chat_guid, thread_id, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (chat_guid, thread_id),
    )
    conn.commit()
    conn.close()


def save_message(chat_guid, sender, message, message_guid):
    """Save a message to the database.
    
    Args:
        chat_guid (str): The chat GUID
        sender (str): The sender identifier
        message (str): The message content
        message_guid (str): The message GUID
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (chat_guid, sender, message, message_guid) VALUES (?, ?, ?, ?)",
        (chat_guid, sender, message, message_guid),
    )
    conn.commit()
    conn.close()


def get_recent_messages(chat_guid, limit=10):
    """Retrieve recent messages.
    
    Args:
        chat_guid (str): The chat GUID
        limit (int): Maximum number of messages to retrieve
        
    Returns:
        list: List of (sender, message) tuples in chronological order
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT sender, message FROM messages 
        WHERE chat_guid = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """,
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    return list(reversed(messages))  # Reverse to get chronological order


def get_message_by_guid(message_guid):
    """Get a message by its GUID.
    
    Args:
        message_guid (str): The message GUID
        
    Returns:
        tuple: (sender, message) or None if not found
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT sender, message FROM messages WHERE message_guid = ?", (message_guid,)
    )
    result = c.fetchone()
    conn.close()
    return result


def get_total_message_count(chat_guid):
    """Get the number of messages in a chat.
    
    Args:
        chat_guid (str): The chat GUID
        
    Returns:
        int: Total message count
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM messages WHERE chat_guid = ?",
        (chat_guid,),
    )
    count = c.fetchone()[0]
    conn.close()
    return count


def save_user_subscription(status, phone_number=None, email=None):
    """Save user subscription information.
    
    Args:
        status (str): Subscription status ('active', 'expired', etc.)
        phone_number (str, optional): User's phone number
        email (str, optional): User's email
        
    Raises:
        ValueError: If neither phone_number nor email is provided
    """
    if not phone_number and not email:
        raise ValueError("Either phone_number or email must be provided")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO subscriptions 
           (phone_number, email, status, subscription_date) 
           VALUES (?, ?, ?, ?)""",
        (phone_number, email, status, datetime.now(timezone.utc)),
    )
    conn.commit()
    conn.close()


def find_latest_chat_guid(identifier):
    """Find the latest chat GUID for a given identifier.
    
    Args:
        identifier (str): User identifier (phone or email)
        
    Returns:
        str: The chat GUID or None if not found
    """
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT chat_guid FROM messages 
        WHERE sender = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """,
        (identifier,),
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def check_subscription_status(phone_number=None, email=None):
    """Check the subscription status for a user.
    
    Args:
        phone_number (str, optional): User's phone number
        email (str, optional): User's email
        
    Returns:
        str: Subscription status or None if not found
    """
    if not phone_number and not email:
        return None
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    if phone_number:
        c.execute(
            "SELECT status FROM subscriptions WHERE phone_number = ?", (phone_number,)
        )
    elif email:
        c.execute("SELECT status FROM subscriptions WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None 