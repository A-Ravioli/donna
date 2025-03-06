import resend

from src.config.settings import (
    RESEND_API_KEY,
    STRIPE_PAYMENT_LINK,
)


class EmailService:
    """Service for sending emails using Resend."""
    
    def __init__(self, api_key=None):
        """
        Initialize the email service.
        
        Args:
            api_key (str, optional): Resend API key.
        """
        self.api_key = api_key or RESEND_API_KEY
        resend.api_key = self.api_key
        
    def send_activation_email(self, to_email, name):
        """
        Send an activation email to a user who has successfully subscribed.
        
        Args:
            to_email (str): The recipient's email address.
            name (str): The recipient's name.
            
        Returns:
            dict: Response from the email API.
        """
        try:
            response = resend.Emails.send({
                "from": "Alfred <alfred@yourdomain.com>",
                "to": to_email,
                "subject": "Welcome to Alfred - Your Subscription is Active!",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #4A90E2;">Welcome to Alfred!</h1>
                    <p>Hello {name},</p>
                    <p>Thank you for subscribing to Alfred. Your subscription is now active!</p>
                    <p>You now have unlimited access to Alfred, your personal assistant.</p>
                    <p>If you have any questions or need assistance, simply text Alfred or reply to this email.</p>
                    <p>Best regards,<br>The Alfred Team</p>
                </div>
                """
            })
            print(f"Activation email sent to {to_email}")
            return response
        except Exception as e:
            print(f"Failed to send activation email: {e}")
            return None
            
    def send_payment_failed_email(self, name, email):
        """
        Send an email notifying user of a failed payment.
        
        Args:
            name (str): The recipient's name.
            email (str): The recipient's email address.
            
        Returns:
            dict: Response from the email API.
        """
        try:
            response = resend.Emails.send({
                "from": "Alfred <alfred@yourdomain.com>",
                "to": email,
                "subject": "Action Required: Alfred Payment Failed",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #E74C3C;">Payment Failed</h1>
                    <p>Hello {name},</p>
                    <p>We were unable to process your recent payment for your Alfred subscription.</p>
                    <p>To continue using Alfred without interruption, please update your payment information:</p>
                    <p><a href="{STRIPE_PAYMENT_LINK}" style="background-color: #4A90E2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Update Payment</a></p>
                    <p>If you need any assistance, please reply to this email.</p>
                    <p>Best regards,<br>The Alfred Team</p>
                </div>
                """
            })
            print(f"Payment failed email sent to {email}")
            return response
        except Exception as e:
            print(f"Failed to send payment failed email: {e}")
            return None
    
    def send_failed_cancellation_email(self, name, email, phone_number=None):
        """
        Send an email notifying user that their subscription has been cancelled.
        
        Args:
            name (str): The recipient's name.
            email (str): The recipient's email address.
            phone_number (str, optional): The recipient's phone number.
            
        Returns:
            dict: Response from the email API.
        """
        try:
            # If we have phone_number, include it in the email
            phone_text = f" (Phone: {phone_number})" if phone_number else ""
            
            response = resend.Emails.send({
                "from": "Alfred <alfred@yourdomain.com>",
                "to": email,
                "subject": "Your Alfred Subscription Has Been Cancelled",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #4A90E2;">Subscription Cancelled</h1>
                    <p>Hello {name}{phone_text},</p>
                    <p>Your subscription to Alfred has been cancelled as requested.</p>
                    <p>We're sad to see you go! If you'd like to reactivate your subscription in the future, you can do so using the link below:</p>
                    <p><a href="{STRIPE_PAYMENT_LINK}" style="background-color: #4A90E2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Resubscribe</a></p>
                    <p>If you have any feedback or questions, please reply to this email - we'd love to hear from you.</p>
                    <p>Best regards,<br>The Alfred Team</p>
                </div>
                """
            })
            print(f"Cancellation email sent to {email}")
            return response
        except Exception as e:
            print(f"Failed to send cancellation email: {e}")
            return None 