import requests
import tempfile
import os
import base64
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from src.config.settings import BLUEBUBBLES_SERVER_ADDR, BLUEBUBBLES_SERVER_PASSWORD


class MessagingService:
    """Service for interacting with the BlueBubbles server."""
    
    def __init__(self, server_addr=None, server_password=None):
        """
        Initialize the messaging service.
        
        Args:
            server_addr (str, optional): The BlueBubbles server address.
            server_password (str, optional): The BlueBubbles server password.
        """
        self.server_addr = server_addr or BLUEBUBBLES_SERVER_ADDR
        self.server_password = server_password or BLUEBUBBLES_SERVER_PASSWORD
        self.base_params = {"password": self.server_password}
        
    def send_text(self, chat_guid: str, message: str, method: str = "private-api") -> Optional[str]:
        """
        Send a text message to a chat via the BlueBubbles server.
        
        Args:
            chat_guid (str): The chat guid to send the message to
            message (str): The text to send
            method (str): The method to use to send the message. Defaults to "private-api"
            
        Returns:
            str: The message_guid of the sent message, or None if an error occurred
        """
        data = {"chatGuid": chat_guid, "message": message, "method": method}
        
        try:
            response = requests.post(
                f"{self.server_addr}/api/v1/message/text",
                json=data,
                params=self.base_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            # Parse the response to get the message_guid
            response_data = response.json()
            return response_data.get("data", {}).get("guid")
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            if hasattr(e, "response") and hasattr(e.response, "text"):
                print(f"Response content: {e.response.text}")
            return None
    
    def share_contact_card(self, chat_guid: str) -> bool:
        """
        Share a contact card in a chat.
        
        Args:
            chat_guid (str): The chat GUID to share the contact card in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = {
                "chatGuid": chat_guid,
                "contactGuids": ["me"],
                "method": "private-api",
            }
            
            response = requests.post(
                f"{self.server_addr}/api/v1/message/share-contact",
                json=data,
                params=self.base_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            print(f"Contact card shared successfully in chat {chat_guid}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sharing contact card: {e}")
            return False
    
    def send_image(self, chat_guid: str, image_path: str, message: Optional[str] = None, method: str = "private-api") -> Optional[str]:
        """
        Send an image to a chat with optional text.
        
        Args:
            chat_guid (str): The chat GUID to send the image to
            image_path (str): The path to the image file
            message (str, optional): Optional text to send with the image
            method (str): The method to use to send the message. Defaults to "private-api"
            
        Returns:
            str: The message_guid of the sent message, or None if an error occurred
        """
        try:
            with open(image_path, "rb") as img_file:
                # Convert to base64
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                
            # Prepare the data
            data = {
                "chatGuid": chat_guid,
                "base64": base64_image,
                "method": method
            }
            
            if message:
                data["message"] = message
                
            # Send the request
            response = requests.post(
                f"{self.server_addr}/api/v1/message/attachment",
                json=data,
                params=self.base_params,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            
            # Parse the response to get the message_guid
            response_data = response.json()
            return response_data.get("data", {}).get("guid")
        except Exception as e:
            print(f"Error sending image: {e}")
            return None
    
    def get_recent_messages(self, chat_guid: str, limit: int = 50, after_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get recent messages from a chat.
        
        Args:
            chat_guid (str): The chat GUID to get messages from
            limit (int, optional): The maximum number of messages to retrieve. Defaults to 50.
            after_date (datetime, optional): Only get messages after this date
            
        Returns:
            List[Dict[str, Any]]: List of messages, or empty list if an error occurred
        """
        try:
            params = {
                **self.base_params,
                "limit": limit,
                "withChats": True,
                "withAttachments": True,
                "withHandles": True,
            }
            
            if after_date:
                # Convert to timestamp in milliseconds
                params["after"] = int(after_date.timestamp() * 1000)
                
            response = requests.get(
                f"{self.server_addr}/api/v1/chat/{chat_guid}/message",
                params=params,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error getting messages: {e}")
            return []
    
    def download_attachment(self, attachment_guid: str, width: int = 800, height: int = 800) -> Optional[bytes]:
        """
        Download an attachment from the BlueBubbles server.
        
        Args:
            attachment_guid (str): The GUID of the attachment to download
            width (int, optional): The width to resize to. Defaults to 800.
            height (int, optional): The height to resize to. Defaults to 800.
            
        Returns:
            bytes: The attachment data, or None if an error occurred
        """
        try:
            params = {
                "password": self.server_password,
                "width": width,
                "height": height,
                "quality": "better",
            }
            
            response = requests.get(
                f"{self.server_addr}/api/v1/attachment/{attachment_guid}/download",
                params=params,
            )
            response.raise_for_status()
            
            # Return the binary data
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Error downloading attachment: {e}")
            return None
    
    def get_chat_details(self, chat_guid: str) -> Optional[Dict[str, Any]]:
        """
        Get details about a chat.
        
        Args:
            chat_guid (str): The GUID of the chat to get details for
            
        Returns:
            Dict[str, Any]: Chat details, or None if an error occurred
        """
        try:
            response = requests.get(
                f"{self.server_addr}/api/v1/chat/{chat_guid}",
                params=self.base_params,
            )
            response.raise_for_status()
            
            return response.json().get("data")
        except requests.exceptions.RequestException as e:
            print(f"Error getting chat details: {e}")
            return None
    
    def get_all_chats(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a list of all chats.
        
        Args:
            limit (int, optional): Maximum number of chats to retrieve. Defaults to 100.
            offset (int, optional): Offset for pagination. Defaults to 0.
            
        Returns:
            List[Dict[str, Any]]: List of chats, or empty list if an error occurred
        """
        try:
            params = {
                **self.base_params,
                "limit": limit,
                "offset": offset,
                "withParticipants": True,
            }
            
            response = requests.get(
                f"{self.server_addr}/api/v1/chat/all",
                params=params,
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error getting chats: {e}")
            return []
    
    def get_chat_by_participant(self, identifier: str) -> Optional[str]:
        """
        Find a chat GUID by participant identifier (phone number or email).
        
        Args:
            identifier (str): The phone number or email to search for
            
        Returns:
            str: The chat GUID if found, None otherwise
        """
        try:
            # Get all chats
            chats = self.get_all_chats(limit=200)  # Increase limit to find more chats
            
            # Clean up the identifier for comparison
            clean_identifier = identifier.replace(" ", "").replace("-", "").replace("+", "")
            
            # Look for a chat with the given participant
            for chat in chats:
                # Skip group chats if they have more than 2 participants (me + 1)
                if chat.get("isGroup", False) and chat.get("participants", []) > 2:
                    continue
                    
                for participant in chat.get("participants", []):
                    address = participant.get("address", "")
                    # Clean up the address for comparison
                    clean_address = address.replace(" ", "").replace("-", "").replace("+", "")
                    
                    if clean_identifier in clean_address or clean_address in clean_identifier:
                        return chat.get("guid")
            
            return None
        except Exception as e:
            print(f"Error finding chat by participant: {e}")
            return None
    
    def mark_as_read(self, chat_guid: str) -> bool:
        """
        Mark all messages in a chat as read.
        
        Args:
            chat_guid (str): The chat GUID to mark as read
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_addr}/api/v1/chat/{chat_guid}/read",
                params=self.base_params,
            )
            response.raise_for_status()
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error marking chat as read: {e}")
            return False 