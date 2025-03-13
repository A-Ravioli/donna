import requests
from donna.config import SERVER_ADDR, SERVER_PASSWORD

def send_text(chat_guid, message, method="private-api"):
    """
    Sends a text message to a chat via the BlueBubbles server.

    Args:
        chat_guid (str): The chat guid to send the message to
        message (str): The text to send
        method (str): The method to use to send the message. Defaults to "private-api"

    Returns:
        str: The message_guid of the sent message, or None if an error occurred
    """
    params = {"password": SERVER_PASSWORD}
    data = {"chatGuid": chat_guid, "message": message, "method": method}

    try:
        response = requests.post(
            f"{SERVER_ADDR}/api/v1/message/text",
            json=data,
            params=params,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        # Parse the response to get the message_guid
        response_data = response.json()
        return response_data.get("data", {}).get("guid")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e.response, "text"):
            print(f"Response content: {e.response.text}")
        return None


def share_contact_card(chat_guid):
    """
    Shares Alfred's contact card with the user via the BlueBubbles API.

    Args:
        chat_guid (str): The chat GUID to share the contact card with

    Returns:
        bool: True if the contact card was shared successfully, False otherwise
    """
    params = {"password": SERVER_PASSWORD}

    try:
        response = requests.post(
            f"{SERVER_ADDR}/api/v1/chat/{chat_guid}/share/contact",
            json={},
            params=params,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sharing contact card: {e}")
        return False


def download_attachment(attachment_guid, width=800, height=800, quality="better"):
    """
    Downloads an attachment from the BlueBubbles server.

    Args:
        attachment_guid (str): The attachment GUID
        width (int): The desired width of the image
        height (int): The desired height of the image
        quality (str): The desired quality of the image

    Returns:
        bytes: The attachment content or None if an error occurred
    """
    params = {
        "password": SERVER_PASSWORD,
        "width": width,
        "height": height,
        "quality": quality,
    }

    try:
        response = requests.get(
            f"{SERVER_ADDR}/api/v1/attachment/{attachment_guid}/download",
            params=params,
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading attachment: {e}")
        return None 