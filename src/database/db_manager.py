import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import os

from src.config.settings import CONVERSATIONS_DB_PATH, USERS_DB_PATH

# Ensure data directory exists
Path(CONVERSATIONS_DB_PATH.parent).mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize the conversations database."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
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
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone_number TEXT UNIQUE,
                  email TEXT UNIQUE,
                  subscription_active INTEGER DEFAULT 0,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    conn.commit()
    conn.close()


def get_thread_id(chat_guid):
    """Get the thread ID for a chat GUID."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT thread_id FROM conversations WHERE chat_guid = ?", (chat_guid,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def save_thread_id(chat_guid, thread_id):
    """Save or update the thread ID for a chat GUID."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT INTO conversations (chat_guid, thread_id, last_updated)
                 VALUES (?, ?, ?) 
                 ON CONFLICT(chat_guid) 
                 DO UPDATE SET thread_id = ?, last_updated = ?""",
        (chat_guid, thread_id, datetime.now(timezone.utc),
         thread_id, datetime.now(timezone.utc)),
    )
    conn.commit()
    conn.close()


def save_message(chat_guid, sender, message, message_guid):
    """Save a message to the database."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """INSERT INTO messages (chat_guid, sender, message, message_guid, timestamp)
                     VALUES (?, ?, ?, ?, ?)""",
            (chat_guid, sender, message, message_guid, datetime.now(timezone.utc)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Message already exists
        pass
    conn.close()


def get_recent_messages(chat_guid, limit=10):
    """Get recent messages for a chat GUID."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT sender, message FROM messages 
                 WHERE chat_guid = ? 
                 ORDER BY timestamp DESC 
                 LIMIT ?""",
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    # Return messages in reverse chronological order (oldest first)
    return list(reversed(messages))


def get_message_by_guid(message_guid):
    """Get a message by its GUID."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT chat_guid, sender, message FROM messages 
                 WHERE message_guid = ?""",
        (message_guid,),
    )
    result = c.fetchone()
    conn.close()
    return result


def get_total_message_count(chat_guid):
    """Get the total number of messages for a chat GUID."""
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT COUNT(*) FROM messages 
                 WHERE chat_guid = ?""",
        (chat_guid,),
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0


def save_user_subscription(status, phone_number=None, email=None):
    """Save or update a user's subscription status."""
    if not phone_number and not email:
        return False
        
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    now = datetime.now(timezone.utc)
    
    try:
        if phone_number:
            c.execute(
                """INSERT INTO users (phone_number, subscription_active, last_updated)
                         VALUES (?, ?, ?) 
                         ON CONFLICT(phone_number) 
                         DO UPDATE SET subscription_active = ?, last_updated = ?""",
                (phone_number, status, now, status, now),
            )
        elif email:
            c.execute(
                """INSERT INTO users (email, subscription_active, last_updated)
                         VALUES (?, ?, ?) 
                         ON CONFLICT(email) 
                         DO UPDATE SET subscription_active = ?, last_updated = ?""",
                (email, status, now, status, now),
            )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


def find_latest_chat_guid(identifier):
    """
    Find the most recently active chat GUID for a given phone number or email.
    
    Args:
        identifier (str): Phone number or email to search for
        
    Returns:
        str: The most recent chat GUID or None
    """
    conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    c = conn.cursor()
    
    # Look for messages with this sender
    c.execute(
        """SELECT chat_guid FROM messages 
                 WHERE sender LIKE ? 
                 ORDER BY timestamp DESC 
                 LIMIT 1""",
        (f"%{identifier}%",),
    )
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None


def check_subscription_status(phone_number=None, email=None):
    """Check if a user has an active subscription."""
    if not phone_number and not email:
        return False
        
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    
    try:
        if phone_number:
            c.execute(
                """SELECT subscription_active FROM users 
                         WHERE phone_number = ?""",
                (phone_number,),
            )
        elif email:
            c.execute(
                """SELECT subscription_active FROM users 
                         WHERE email = ?""",
                (email,),
            )
            
        result = c.fetchone()
        return bool(result[0]) if result else False
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


def get_all_active_subscribers():
    """Get all active subscribers."""
    conn = sqlite3.connect(USERS_DB_PATH)
    c = conn.cursor()
    
    c.execute(
        """SELECT phone_number, email FROM users 
                 WHERE subscription_active = 1"""
    )
    
    subscribers = c.fetchall()
    conn.close()
    
    return subscribers


def get_db_info():
    """Get information about the database for status reporting."""
    conversations_conn = sqlite3.connect(CONVERSATIONS_DB_PATH)
    users_conn = sqlite3.connect(USERS_DB_PATH)
    
    c_conversations = conversations_conn.cursor()
    c_users = users_conn.cursor()
    
    # Get conversation count
    c_conversations.execute("SELECT COUNT(*) FROM conversations")
    conversation_count = c_conversations.fetchone()[0]
    
    # Get message count
    c_conversations.execute("SELECT COUNT(*) FROM messages")
    message_count = c_conversations.fetchone()[0]
    
    # Get user count
    c_users.execute("SELECT COUNT(*) FROM users")
    user_count = c_users.fetchone()[0]
    
    # Get active subscription count
    c_users.execute("SELECT COUNT(*) FROM users WHERE subscription_active = 1")
    subscription_count = c_users.fetchone()[0]
    
    conversations_conn.close()
    users_conn.close()
    
    return {
        "conversation_count": conversation_count,
        "message_count": message_count,
        "user_count": user_count,
        "subscription_count": subscription_count,
    } 