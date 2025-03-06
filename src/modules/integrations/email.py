import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import re

from .base import BaseIntegration

class EmailIntegration(BaseIntegration):
    """Integration for managing emails."""
    
    def get_name(self) -> str:
        return "Email"
    
    def get_commands(self) -> List[str]:
        return [
            "send email",
            "check email",
            "read email",
            "list emails",
            "search emails",
            "setup email"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS email_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            imap_server TEXT,
            smtp_server TEXT,
            email_address TEXT,
            display_name TEXT,
            last_email_check DATETIME
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
                
        # Also check for common email-related phrases
        email_phrases = [
            "send a message to",
            "email to",
            "forward this to",
            "send this email",
            "my inbox",
            "unread emails",
            "check my email"
        ]
        
        for phrase in email_phrases:
            if phrase in message_lower:
                return True
                
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Handle setup command
        if "setup email" in message_lower:
            # Extract email credentials from the message
            # This is a simplified version - in a real system, you would use a more secure method
            email_match = re.search(r'email:?\s*([^\s,]+@[^\s,]+)', message)
            password_match = re.search(r'password:?\s*([^\s,]+)', message)
            
            if email_match and password_match:
                email_address = email_match.group(1)
                password = password_match.group(1)
                
                # Try to determine email provider
                provider = self._determine_email_provider(email_address)
                
                # Store credentials
                credentials = {
                    "email": email_address,
                    "password": password,  # In a real system, encrypt this!
                    "imap_server": provider["imap"],
                    "smtp_server": provider["smtp"]
                }
                
                if self.store_credentials(user_id, credentials):
                    # Update email settings
                    self._update_email_settings(
                        user_id, 
                        provider["imap"], 
                        provider["smtp"], 
                        email_address
                    )
                    
                    return f"Your email {email_address} has been successfully set up! You can now send and receive emails through donna."
                else:
                    return "There was an error setting up your email. Please try again."
            else:
                return "To set up your email, please provide your email address and password like this: 'setup email email:youremail@example.com password:yourpassword'"
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get the user's credentials
        credentials = self.get_credentials(user_id)
        
        # Handle send email command
        if "send email" in message_lower or "send a message to" in message_lower or "email to" in message_lower:
            # Extract recipient, subject, and body
            to_match = re.search(r'to:?\s*([^\s,]+@[^\s,]+)', message)
            subject_match = re.search(r'subject:?\s*([^,\.]+)', message)
            body_match = re.search(r'body:?\s*(.+)', message, re.DOTALL)
            
            if not to_match:
                # Try to find an email address in the message
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
                if email_match:
                    to_email = email_match.group(1)
                else:
                    return "Please specify a recipient email address using 'to: email@example.com'."
            else:
                to_email = to_match.group(1)
                
            subject = subject_match.group(1) if subject_match else "Message from donna"
            body = body_match.group(1) if body_match else "This email was sent via donna assistant."
            
            # If there's no explicit body but there's content after "to: email@example.com",
            # use that as the body
            if not body_match and to_match:
                remaining_text = message[to_match.end():]
                if subject_match:
                    remaining_text = remaining_text[subject_match.end():]
                
                if remaining_text.strip():
                    body = remaining_text.strip()
            
            # Send the email
            try:
                self._send_email(
                    credentials["smtp_server"], 
                    credentials["email"], 
                    credentials["password"], 
                    to_email, 
                    subject, 
                    body
                )
                return f"Email sent to {to_email} with subject '{subject}'."
            except Exception as e:
                return f"Error sending email: {str(e)}"
        
        # Handle check/read email command
        elif "check email" in message_lower or "read email" in message_lower or "list emails" in message_lower:
            try:
                limit = 5  # Default to 5 emails
                
                # Try to find a number in the message
                num_match = re.search(r'(\d+)\s+emails', message_lower)
                if num_match:
                    limit = int(num_match.group(1))
                    limit = min(limit, 20)  # Cap at 20 for performance
                
                # Check if we should only show unread emails
                unread_only = "unread" in message_lower
                
                # Fetch emails
                emails = self._fetch_emails(
                    credentials["imap_server"], 
                    credentials["email"], 
                    credentials["password"], 
                    limit=limit, 
                    unread_only=unread_only
                )
                
                if not emails:
                    if unread_only:
                        return "You have no unread emails."
                    else:
                        return "You have no emails in your inbox."
                
                # Format emails for display
                response = f"Here are your {'unread ' if unread_only else ''}latest {len(emails)} emails:\n\n"
                
                for i, email_data in enumerate(emails):
                    response += f"{i+1}. From: {email_data['from']}\n"
                    response += f"   Subject: {email_data['subject']}\n"
                    response += f"   Date: {email_data['date']}\n"
                    
                    # Add a snippet of the body
                    if email_data['body']:
                        snippet = email_data['body'][:100].replace('\n', ' ')
                        response += f"   {snippet}{'...' if len(email_data['body']) > 100 else ''}\n"
                    
                    response += "\n"
                
                response += "To read the full content of an email, say 'read email 1' (or the number of the email you want to read)."
                
                return response
            except Exception as e:
                return f"Error checking emails: {str(e)}"
        
        # Handle search emails command
        elif "search emails" in message_lower:
            search_term_match = re.search(r'search emails (?:for )?["\']?([^"\']+)["\']?', message_lower)
            
            if not search_term_match:
                return "Please specify a search term, e.g., 'search emails for meeting'"
            
            search_term = search_term_match.group(1)
            
            try:
                # Fetch emails matching the search term
                emails = self._search_emails(
                    credentials["imap_server"], 
                    credentials["email"], 
                    credentials["password"], 
                    search_term
                )
                
                if not emails:
                    return f"No emails found matching '{search_term}'."
                
                # Format emails for display
                response = f"Here are emails matching '{search_term}':\n\n"
                
                for i, email_data in enumerate(emails[:5]):  # Limit to 5 results
                    response += f"{i+1}. From: {email_data['from']}\n"
                    response += f"   Subject: {email_data['subject']}\n"
                    response += f"   Date: {email_data['date']}\n"
                    
                    # Add a snippet of the body
                    if email_data['body']:
                        snippet = email_data['body'][:100].replace('\n', ' ')
                        response += f"   {snippet}{'...' if len(email_data['body']) > 100 else ''}\n"
                    
                    response += "\n"
                
                if len(emails) > 5:
                    response += f"Showing 5 of {len(emails)} matching emails."
                
                return response
            except Exception as e:
                return f"Error searching emails: {str(e)}"
        
        # If we get here, no command matched
        return "I didn't understand your email request. You can say 'send email to person@example.com', 'check email', or 'search emails for [term]'."
    
    def _determine_email_provider(self, email_address: str) -> Dict[str, str]:
        """
        Determine email provider settings based on email address.
        
        Args:
            email_address: The email address
            
        Returns:
            dict: Provider settings
        """
        domain = email_address.split('@')[1].lower()
        
        providers = {
            "gmail.com": {
                "imap": "imap.gmail.com",
                "smtp": "smtp.gmail.com"
            },
            "outlook.com": {
                "imap": "outlook.office365.com",
                "smtp": "smtp-mail.outlook.com"
            },
            "hotmail.com": {
                "imap": "outlook.office365.com",
                "smtp": "smtp-mail.outlook.com"
            },
            "yahoo.com": {
                "imap": "imap.mail.yahoo.com",
                "smtp": "smtp.mail.yahoo.com"
            }
        }
        
        # Return the provider settings if found, otherwise use a generic setting
        return providers.get(domain, {"imap": f"imap.{domain}", "smtp": f"smtp.{domain}"})
    
    def _update_email_settings(self, user_id: str, imap_server: str, smtp_server: str, email_address: str) -> bool:
        """
        Update email settings for a user.
        
        Args:
            user_id: The ID of the user
            imap_server: The IMAP server
            smtp_server: The SMTP server
            email_address: The email address
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            # Get display name from email address
            display_name = email_address.split('@')[0]
            
            c.execute('''
                INSERT OR REPLACE INTO email_settings
                (user_id, imap_server, smtp_server, email_address, display_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, imap_server, smtp_server, email_address, display_name))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating email settings: {e}")
            return False
    
    def _send_email(self, smtp_server: str, from_email: str, password: str, to_email: str, subject: str, body: str) -> bool:
        """
        Send an email.
        
        Args:
            smtp_server: The SMTP server
            from_email: The sender email
            password: The sender password
            to_email: The recipient email
            subject: The email subject
            body: The email body
            
        Returns:
            bool: True if successful
        """
        # Create a multipart message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session
        with smtplib.SMTP(smtp_server, 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
        
        return True
    
    def _fetch_emails(self, imap_server: str, email_address: str, password: str, limit: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch emails from an IMAP server.
        
        Args:
            imap_server: The IMAP server
            email_address: The email address
            password: The password
            limit: The maximum number of emails to fetch
            unread_only: Whether to fetch only unread emails
            
        Returns:
            list: A list of email data dictionaries
        """
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select('inbox')
        
        # Search for emails
        if unread_only:
            status, data = mail.search(None, 'UNSEEN')
        else:
            status, data = mail.search(None, 'ALL')
        
        email_ids = data[0].split()
        
        # Get the latest emails up to the limit
        latest_emails = email_ids[-limit:] if limit < len(email_ids) else email_ids
        
        result = []
        
        for email_id in reversed(latest_emails):
            status, data = mail.fetch(email_id, '(RFC822)')
            
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract email data
            email_data = {
                'from': email_message['From'],
                'to': email_message['To'],
                'subject': email_message['Subject'],
                'date': email_message['Date'],
                'body': ''
            }
            
            # Get the body of the email
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))
                    
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        email_data['body'] = part.get_payload(decode=True).decode()
                        break
            else:
                email_data['body'] = email_message.get_payload(decode=True).decode()
            
            result.append(email_data)
        
        mail.close()
        mail.logout()
        
        return result
    
    def _search_emails(self, imap_server: str, email_address: str, password: str, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for emails containing a term.
        
        Args:
            imap_server: The IMAP server
            email_address: The email address
            password: The password
            search_term: The term to search for
            
        Returns:
            list: A list of matching email data dictionaries
        """
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select('inbox')
        
        # Search for emails - this is a simple implementation
        # In a real-world scenario, you'd use more sophisticated search criteria
        status, data = mail.search(None, 'ALL')
        
        email_ids = data[0].split()
        result = []
        
        # Search through emails
        for email_id in reversed(email_ids):
            status, data = mail.fetch(email_id, '(RFC822)')
            
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract email data
            email_data = {
                'from': email_message['From'],
                'to': email_message['To'],
                'subject': email_message['Subject'],
                'date': email_message['Date'],
                'body': ''
            }
            
            # Get the body of the email
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))
                    
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        email_data['body'] = part.get_payload(decode=True).decode()
                        break
            else:
                email_data['body'] = email_message.get_payload(decode=True).decode()
            
            # Check if the search term is in the subject or body
            if (search_term.lower() in email_data['subject'].lower() or 
                search_term.lower() in email_data['body'].lower() or
                search_term.lower() in email_data['from'].lower()):
                result.append(email_data)
        
        mail.close()
        mail.logout()
        
        return result 