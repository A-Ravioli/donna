import requests
import tempfile

from config import SERVER_ADDR, SERVER_PASSWORD, WELCOME_MESSAGE
from db.db_setup import save_message


def send_text(chat_guid, message, method="private-api"):
    params = {"password": SERVER_PASSWORD}
    data = {"chatGuid": chat_guid, "message": message, "method": method}
    try:
        response = requests.post(
            f"{SERVER_ADDR}/api/v1/message/text",
            json=data,
            params=params,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("data", {}).get("guid")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        if hasattr(e.response, "text"):
            print(f"Response content: {e.response.text}")
        return None


def share_contact_card(chat_guid):
    params = {"password": SERVER_PASSWORD}
    try:
        response = requests.post(
            f"{SERVER_ADDR}/api/v1/chat/{chat_guid}/share/contact",
            json={},
            params=params,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sharing contact card: {e}")
        return False


def process_attachments(attachments):
    for attachment in attachments:
        if attachment.get("mimeType", "").startswith("image/"):
            try:
                params = {"password": SERVER_PASSWORD, "width": 800, "height": 800, "quality": "better"}
                response = requests.get(
                    f"{SERVER_ADDR}/api/v1/attachment/{attachment['guid']}/download",
                    params=params
                )
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                return temp_file_path
            except requests.exceptions.RequestException as e:
                print(f"Error downloading attachment: {e}")
    return None


def send_welcome_message(chat_guid):
    if share_contact_card(chat_guid):
        print(f"Contact card shared with chat_guid: {chat_guid}")
    else:
        print(f"Failed to share contact card with chat_guid: {chat_guid}")
    message_guid = send_text(chat_guid, WELCOME_MESSAGE)
    if message_guid:
        save_message(chat_guid, "alfred@gtfol.inc", WELCOME_MESSAGE, message_guid)
        print(f"Welcome message sent to chat_guid: {chat_guid}")
    else:
        print(f"Failed to send welcome message to chat_guid: {chat_guid}") 