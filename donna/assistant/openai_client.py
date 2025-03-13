import openai
import tempfile
from time import sleep
from donna.config import OPENAI_API_KEY, ALFRED_ASSISTANT_ID
from donna.database.models import get_thread_id, save_thread_id, get_recent_messages

# Initialize the OpenAI client
openai.api_key = OPENAI_API_KEY

def process_image_attachment(attachment_content):
    """
    Processes an image attachment and uploads it to OpenAI.

    Args:
        attachment_content (bytes): The raw image content

    Returns:
        str: OpenAI file ID or None if unsuccessful
    """
    try:
        # Save the image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(attachment_content)
            temp_file_path = temp_file.name

        # Upload the image to OpenAI
        with open(temp_file_path, "rb") as file:
            openai_file = openai.files.create(file=file, purpose="vision")

        return openai_file.id
    except Exception as e:
        print(f"Error uploading file to OpenAI: {e}")
        return None


def create_assistant_response(chat_guid, message, file_id=None, is_group_chat=False):
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

        # If it's a group chat, include recent messages for context
        if is_group_chat:
            recent_messages = get_recent_messages(chat_guid, 15)
            if recent_messages:
                context = "Here are the recent messages in the group chat:\n\n"
                for sender, msg in recent_messages:
                    context += f"{sender}: {msg}\n"
                context += "\nPlease consider this context when responding to the following message:\n"
                content.append({"type": "text", "text": context})

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

        openai.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=content
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=ALFRED_ASSISTANT_ID
        )

        # Wait for the run to complete
        while run.status != "completed":
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            sleep(1)

        # Retrieve Alfred's response
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_response = messages.data[0].content[0].text.value

        return assistant_response
    except Exception as e:
        print(f"❌ Error processing message with OpenAI Assistant: {e}")
        return "I'm sorry, I encountered an error while processing your message." 