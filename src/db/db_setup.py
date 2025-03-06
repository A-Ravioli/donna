import sqlite3
from datetime import datetime, timezone


def init_db():
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
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("SELECT thread_id FROM conversations WHERE chat_guid = ?", (chat_guid,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def save_thread_id(chat_guid, thread_id):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO conversations (chat_guid, thread_id, last_updated) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (chat_guid, thread_id),
    )
    conn.commit()
    conn.close()


def save_message(chat_guid, sender, message, message_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (chat_guid, sender, message, message_guid) VALUES (?, ?, ?, ?)",
        (chat_guid, sender, message, message_guid),
    )
    conn.commit()
    conn.close()


def get_recent_messages(chat_guid, limit=10):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT sender, message FROM messages WHERE chat_guid = ? ORDER BY timestamp DESC LIMIT ?",
        (chat_guid, limit),
    )
    messages = c.fetchall()
    conn.close()
    return list(reversed(messages))  # chronological order


def get_message_by_guid(message_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("SELECT sender, message FROM messages WHERE message_guid = ?", (message_guid,))
    result = c.fetchone()
    conn.close()
    return result


def get_total_message_count(chat_guid):
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE chat_guid = ?", (chat_guid,))
    count = c.fetchone()[0]
    conn.close()
    return count


def save_user_subscription(status, phone_number=None, email=None):
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
    conn = sqlite3.connect("conversations.db")
    c = conn.cursor()
    c.execute(
        "SELECT chat_guid FROM messages WHERE sender = ? ORDER BY timestamp DESC LIMIT 1",
        (identifier,),
    )
    result = c.fetchone()
    conn.close()
    return result[0] if result else None 