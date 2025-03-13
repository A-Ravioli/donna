import resend
from donna.config import RESEND_API_KEY

# Initialize the Resend client
resend.api_key = RESEND_API_KEY

def send_activation_email(to_email, name):
    """
    Sends an activation email to a user who has paid but not set up their iMessage account.

    Args:
        to_email (str): The email to send to
        name (str): The name of the user

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = "Action Required: Activate Your Alfred Subscription"
    body = f"""
    Hi {name},<br /><br />

    I was unable to find the iMessage account associated with the email ({to_email}) linked to your Stripe payment.<br /><br />
    
    <b>To activate me, please reply to this email with your iMessage account (either phone number or email).</b><br /><br />
    
    If you have any questions, feel free to contact our support team at team@gtfol.inc.<br /><br />

    Best,<br />
    Alfred<br /><br />

    <a href="https://alfredagent.com">Alfred — Your In-House COO</a>
    """

    try:
        resend.Emails.send(
            {
                "from": "Alfred <alfred@mail.gtfol.inc>",
                "to": [to_email],
                "cc": ["team@gtfol.inc"],
                "subject": subject,
                "html": body,
            }
        )
        print(f"Notification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send notification email: {e}")
        return False


def send_failed_cancellation_email(name, email, phone_number):
    """
    Sends an email to the team when a subscription cancellation fails.

    Args:
        name (str): The name of the user
        email (str): The email of the user
        phone_number (str): The phone number of the user

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    subject = "Failed: Alfred Subscription Cancellation"
    body = f"""
    Hi,<br /><br />

    The user <b>{name}</b> has cancelled their Alfred subscription. However, I was unable to update the subscription status in my database. Please check the user's details and update the status manually.<br /><br />

    Here are the details of the user:<br />
    <ul>
        <li>Name: {name}</li>
        <li>Email: {email}</li>
        <li>Phone Number: {phone_number}</li>
    </ul><br /><br />

    Best,<br />
    Alfred<br /><br />

    <a href="https://alfredagent.com">Alfred — Your In-House COO</a>
    """

    try:
        resend.Emails.send(
            {
                "from": "Alfred <alfred@mail.gtfol.inc>",
                "to": ["team@gtfol.inc"],
                "subject": subject,
                "html": body,
            }
        )
        print(f"Notification email sent to team@gtfol.inc")
        return True
    except Exception as e:
        print(f"Failed to send notification email: {e}")
        return False 