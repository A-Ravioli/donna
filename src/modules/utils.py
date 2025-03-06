import requests
import tempfile
import os
import resend
from datetime import datetime, timezone

# BlueBubbles server address and password
server_addr = "http://localhost:1234"
server_password = os.getenv("BLUEBUBBLES_SERVER_PASSWORD")

# Resend for sending emails
resend.api_key = os.getenv("RESEND_API_KEY")

def send_text(chat_guid, message, method="private-api"):
    """
    Send a text message to a chat.
    
    Args:
        chat_guid (str): The chat GUID to send the message to
        message (str): The message to send
        method (str): The method to use for sending the message
        
    Returns:
        str: The message GUID, or None if failed
    """
    try:
        # Parameters for the message
        params = {
            "password": server_password,
            "chatGuid": chat_guid,
            "message": message,
            "method": method,
            "effectId": 0,  # No effect
        }

        # Send the message
        response = requests.post(f"{server_addr}/api/v1/message/text", params=params)
        response.raise_for_status()
        
        # Get the message GUID from the response
        response_data = response.json()
        if response_data.get("status") == 200:
            return response_data.get("data", {}).get("tempGuid")
        else:
            print(f"Error sending message: {response_data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None

def share_contact_card(chat_guid):
    """
    Share a contact card with a chat.
    
    Args:
        chat_guid (str): The chat GUID to share the contact with
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parameters for sharing the contact
        params = {
            "password": server_password,
            "chatGuid": chat_guid,
            "contact": "Alfred Butler",
        }

        # Share the contact
        response = requests.post(
            f"{server_addr}/api/v1/message/share-contact", params=params
        )
        response.raise_for_status()
        
        # Check if the request was successful
        response_data = response.json()
        if response_data.get("status") == 200:
            return True
        else:
            print(f"Error sharing contact: {response_data.get('message')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sharing contact: {e}")
        return False

def send_activation_email(to_email, name):
    """
    Send an activation email to a new user.
    
    Args:
        to_email (str): The email address to send to
        name (str): The user's name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Email parameters
        params = {
            "from": "Alfred <alfred@getfromtheotherlane.com>",
            "to": to_email,
            "subject": "Welcome to Alfred!",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Welcome to Alfred, {name}!</h2>
                <p>Your subscription is now active. You can text Alfred at any time for assistance.</p>
                <p>For any questions or issues, just reply to this email.</p>
                <p>Best regards,<br>Alfred</p>
            </div>
            """,
        }

        # Send the email
        response = resend.Emails.send(params)
        
        return True if response.id else False
    except Exception as e:
        print(f"Error sending activation email: {e}")
        return False

def send_failed_cancellation_email(name, email, phone_number):
    """
    Send an email when cancellation fails.
    
    Args:
        name (str): The user's name
        email (str): The user's email
        phone_number (str): The user's phone number
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Current date/time
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Email parameters
        params = {
            "from": "Alfred <alfred@getfromtheotherlane.com>",
            "to": "team@getfromtheotherlane.com",  # Notify the team
            "subject": "Failed Subscription Cancellation",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Failed Subscription Cancellation</h2>
                <p>A user tried to cancel their subscription, but the cancellation failed.</p>
                <p><strong>User Information:</strong></p>
                <ul>
                    <li>Name: {name}</li>
                    <li>Email: {email}</li>
                    <li>Phone: {phone_number}</li>
                    <li>Time: {current_time}</li>
                </ul>
                <p>Please investigate and take appropriate action.</p>
            </div>
            """,
        }

        # Send the email
        response = resend.Emails.send(params)
        
        return True if response.id else False
    except Exception as e:
        print(f"Error sending failed cancellation email: {e}")
        return False

def download_and_process_attachment(attachment):
    """
    Download and process an attachment.
    
    Args:
        attachment (dict): The attachment information
        
    Returns:
        str: The path to the temporary file, or None if failed
    """
    try:
        # Parameters for image resizing and quality
        params = {
            "password": server_password,
            "width": 800,  # Adjust this value as needed
            "height": 800,  # Adjust this value as needed
            "quality": "better",
        }

        response = requests.get(
            f"{server_addr}/api/v1/attachment/{attachment['guid']}/download",
            params=params,
        )
        response.raise_for_status()

        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".jpg"
        ) as temp_file:
            temp_file.write(response.content)
            return temp_file.name
    except requests.exceptions.RequestException as e:
        print(f"Error downloading attachment: {e}")
        return None
    except Exception as e:
        print(f"Error processing attachment: {e}")
        return None 