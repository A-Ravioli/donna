import re
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests

from .base import BaseIntegration

class SlackTeamsIntegration(BaseIntegration):
    """Integration for Slack and Microsoft Teams communications."""
    
    def get_name(self) -> str:
        return "Slack/Teams"
    
    def get_commands(self) -> List[str]:
        return [
            "send slack message",
            "message on slack",
            "post to slack",
            "send teams message",
            "message on teams",
            "post to teams",
            "setup slack",
            "setup teams",
            "check slack",
            "check teams",
            "slack status",
            "teams status"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS messaging_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            platform TEXT,
            workspace TEXT,
            default_channel TEXT,
            team_id TEXT,
            last_message_timestamp DATETIME,
            notification_preferences TEXT
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
        
        # Check for platform mentions
        platforms = ["slack", "teams", "microsoft teams"]
        for platform in platforms:
            if platform in message_lower:
                # Look for action indicators
                action_words = ["send", "post", "message", "check", "status", "write", "tell"]
                for action in action_words:
                    if action in message_lower:
                        return True
        
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Determine which platform is being used
        is_slack = "slack" in message_lower
        is_teams = "teams" in message_lower or "microsoft teams" in message_lower
        
        if not is_slack and not is_teams:
            # Default to slack if not specified
            is_slack = True
        
        platform = "slack" if is_slack else "teams"
        platform_name = "Slack" if is_slack else "Microsoft Teams"
        
        # Handle setup command
        if f"setup {platform}" in message_lower:
            # Extract workspace name if provided
            workspace = None
            workspace_match = re.search(r'workspace(?:\s+(?:is|:))?\s+([^,\.]+)', message_lower)
            
            if workspace_match:
                workspace = workspace_match.group(1).strip()
            else:
                # Use default workspace name
                workspace = "Primary Workspace"
            
            # Extract default channel if provided
            default_channel = None
            channel_match = re.search(r'channel(?:\s+(?:is|:))?\s+([^,\.]+)', message_lower)
            
            if channel_match:
                default_channel = channel_match.group(1).strip()
                # Remove # if present
                if default_channel.startswith("#"):
                    default_channel = default_channel[1:]
            else:
                # Use default channel name
                default_channel = "general"
            
            # In a real implementation, we would start an OAuth flow
            # For this example, we'll just save some basic preferences
            
            # Store credentials (API tokens would go here in a real implementation)
            credentials = {
                "platform": platform,
                "token": "placeholder_token",
                "refresh_token": "placeholder_refresh_token" if is_teams else None,
                "expiry": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            if self.store_credentials(user_id, credentials):
                self._update_messaging_settings(
                    user_id,
                    platform,
                    workspace,
                    default_channel
                )
                
                response = f"Your {platform_name} integration has been set up! "
                response += f"I'll use the workspace '{workspace}' and default channel '{default_channel}'. "
                response += f"You can now send {platform_name} messages through donna by saying 'Send a {platform_name} message to [channel]'."
                
                return response
            else:
                return f"There was an error setting up your {platform_name} integration. Please try again."
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get user credentials and settings
        credentials = self.get_credentials(user_id)
        settings = self._get_messaging_settings(user_id)
        
        # Override platform if user has different platform set up
        stored_platform = credentials.get("platform")
        if stored_platform and stored_platform != platform:
            if f"{platform_name} is not set up" in message_lower:
                return f"You don't have {platform_name} set up. You currently have {stored_platform.capitalize()} configured. Would you like to set up {platform_name} now?"
            
            platform = stored_platform
            platform_name = "Slack" if platform == "slack" else "Microsoft Teams"
            is_slack = platform == "slack"
            is_teams = platform == "teams"
        
        # Handle sending messages
        if any(cmd in message_lower for cmd in ["send message", "post to", "message on", "write", "tell"]):
            # Extract channel/recipient
            channel = settings.get("default_channel", "general")
            channel_match = re.search(r'(?:to|in|on)\s+(?:channel\s+)?(?:#)?([a-zA-Z0-9_-]+)', message_lower)
            
            if channel_match:
                channel = channel_match.group(1).strip()
            
            # Extract message content
            content = None
            content_match = re.search(r'(?:say|post|send|write|tell)(?:\s+that)?\s+["\']([^"\']+)["\']', message)
            
            if content_match:
                content = content_match.group(1)
            else:
                # Look for message after relevant keywords
                message_keywords = ["saying", "that says", "with message", "with text"]
                for keyword in message_keywords:
                    if keyword in message_lower:
                        keyword_pos = message_lower.find(keyword) + len(keyword)
                        content = message[keyword_pos:].strip()
                        break
            
            if not content:
                # Try to extract everything after the channel
                if channel_match:
                    channel_end_pos = message_lower.find(channel) + len(channel)
                    content = message[channel_end_pos:].strip()
                    
                    # Clean up the content
                    content = re.sub(r'^[,:\s]+', '', content)
            
            if not content:
                return f"What message would you like to send to the '{channel}' channel on {platform_name}?"
            
            # Send the message (mock implementation)
            timestamp = datetime.now().isoformat()
            self._update_last_message(user_id, timestamp)
            
            if is_slack:
                return f"I've sent your message to the #{channel} channel on {platform_name}:\n\n\"{content}\""
            else:
                return f"I've posted your message to the {channel} channel on {platform_name}:\n\n\"{content}\""
        
        # Handle checking statuses
        elif any(cmd in message_lower for cmd in ["check", "status"]):
            workspace = settings.get("workspace", "Primary Workspace")
            
            # Generate mock notifications
            notifications = self._generate_mock_notifications(platform, 3)
            
            if not notifications:
                return f"You have no new notifications on {platform_name}."
            
            response = f"Here are your recent notifications from {platform_name} ({workspace}):\n\n"
            
            for notification in notifications:
                response += f"• {notification['sender']} in #{notification['channel']}: \"{notification['message']}\"\n"
                response += f"  {notification['time_ago']} ago\n\n"
            
            return response
        
        # If we get here, no command matched
        return f"I couldn't understand your {platform_name} request. You can say things like 'Send a {platform_name} message to #general' or 'Check my {platform_name} notifications'."
    
    def _update_messaging_settings(self, user_id: str, platform: str, workspace: str, default_channel: str, team_id: str = None) -> bool:
        """
        Update messaging settings for a user.
        
        Args:
            user_id: The user ID
            platform: The messaging platform (slack/teams)
            workspace: The workspace name
            default_channel: The default channel
            team_id: The team ID (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            # Check for existing settings
            c.execute("SELECT * FROM messaging_settings WHERE user_id = ?", (user_id,))
            existing = c.fetchone()
            
            if existing:
                # Update existing record
                c.execute('''
                    UPDATE messaging_settings
                    SET platform = ?, workspace = ?, default_channel = ?
                    WHERE user_id = ?
                ''', (platform, workspace, default_channel, user_id))
            else:
                # Insert new record
                c.execute('''
                    INSERT INTO messaging_settings
                    (user_id, platform, workspace, default_channel, team_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, platform, workspace, default_channel, team_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating messaging settings: {e}")
            return False
    
    def _update_last_message(self, user_id: str, timestamp: str) -> bool:
        """
        Update the last message timestamp.
        
        Args:
            user_id: The user ID
            timestamp: The message timestamp
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            c.execute('''
                UPDATE messaging_settings
                SET last_message_timestamp = ?
                WHERE user_id = ?
            ''', (timestamp, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating last message timestamp: {e}")
            return False
    
    def _get_messaging_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get messaging settings for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            dict: The messaging settings
        """
        try:
            c = self.conn.cursor()
            
            c.execute("SELECT * FROM messaging_settings WHERE user_id = ?", (user_id,))
            record = c.fetchone()
            
            if record:
                return {
                    "platform": record[2],
                    "workspace": record[3],
                    "default_channel": record[4],
                    "team_id": record[5],
                    "last_message_timestamp": record[6],
                    "notification_preferences": record[7]
                }
            
            return {}
        except Exception as e:
            print(f"Error getting messaging settings: {e}")
            return {}
    
    def _generate_mock_notifications(self, platform: str, count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate mock notifications for demonstration purposes.
        
        Args:
            platform: The messaging platform
            count: The number of notifications to generate
            
        Returns:
            list: A list of notification dictionaries
        """
        if count <= 0:
            return []
        
        notifications = []
        
        # Generate names based on platform
        slack_names = ["johndoe", "sarahjane", "michaelb", "emilyw", "davidm", "jessicah"]
        teams_names = ["John Doe", "Sarah Jane", "Michael Brown", "Emily Wilson", "David Miller", "Jessica Hall"]
        
        channels = ["general", "random", "announcements", "development", "marketing", "sales", "support"]
        
        messages = [
            "Hey, can someone review my PR?",
            "Meeting in 15 minutes!",
            "Just pushed the new release",
            "Who's handling the client demo tomorrow?",
            "Website is down, investigating now",
            "New documentation is available",
            "Don't forget to submit your timesheet",
            "Lunch order is here in the kitchen",
            "Great job on the presentation today!",
            "Anyone seen the latest metrics?"
        ]
        
        time_frames = [
            "1 minute", "2 minutes", "5 minutes", "10 minutes", "15 minutes", 
            "30 minutes", "1 hour", "2 hours", "3 hours", "4 hours"
        ]
        
        for i in range(count):
            if platform == "slack":
                sender = slack_names[i % len(slack_names)]
            else:
                sender = teams_names[i % len(teams_names)]
            
            channel = channels[i % len(channels)]
            message = messages[i % len(messages)]
            time_ago = time_frames[i % len(time_frames)]
            
            notifications.append({
                "sender": sender,
                "channel": channel,
                "message": message,
                "time_ago": time_ago
            })
        
        return notifications


class DiscordIntegration(BaseIntegration):
    """Integration for Discord communications."""
    
    def get_name(self) -> str:
        return "Discord"
    
    def get_commands(self) -> List[str]:
        return [
            "send discord message",
            "message on discord",
            "post to discord",
            "setup discord",
            "check discord",
            "discord status"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS discord_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            server_name TEXT,
            default_channel TEXT,
            server_id TEXT,
            last_message_timestamp DATETIME,
            notification_preferences TEXT
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
        
        # Check for Discord mentions
        if "discord" in message_lower:
            # Look for action indicators
            action_words = ["send", "post", "message", "check", "status", "write", "tell"]
            for action in action_words:
                if action in message_lower:
                    return True
        
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Handle setup command
        if "setup discord" in message_lower:
            # Extract server name if provided
            server_name = None
            server_match = re.search(r'server(?:\s+(?:is|:))?\s+([^,\.]+)', message_lower)
            
            if server_match:
                server_name = server_match.group(1).strip()
            else:
                # Use default server name
                server_name = "Main Server"
            
            # Extract default channel if provided
            default_channel = None
            channel_match = re.search(r'channel(?:\s+(?:is|:))?\s+([^,\.]+)', message_lower)
            
            if channel_match:
                default_channel = channel_match.group(1).strip()
                # Remove # if present
                if default_channel.startswith("#"):
                    default_channel = default_channel[1:]
            else:
                # Use default channel name
                default_channel = "general"
            
            # In a real implementation, we would start an OAuth flow
            # For this example, we'll just save some basic preferences
            
            # Store credentials (API tokens would go here in a real implementation)
            credentials = {
                "token": "placeholder_discord_token",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            if self.store_credentials(user_id, credentials):
                self._update_discord_settings(
                    user_id,
                    server_name,
                    default_channel
                )
                
                response = "Your Discord integration has been set up! "
                response += f"I'll use the server '{server_name}' and default channel '#{default_channel}'. "
                response += "You can now send Discord messages through donna by saying 'Send a Discord message to [channel]'."
                
                return response
            else:
                return "There was an error setting up your Discord integration. Please try again."
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get user credentials and settings
        settings = self._get_discord_settings(user_id)
        
        # Handle sending messages
        if any(cmd in message_lower for cmd in ["send message", "post to", "message on", "write", "tell"]):
            # Extract channel/recipient
            channel = settings.get("default_channel", "general")
            channel_match = re.search(r'(?:to|in|on)\s+(?:channel\s+)?(?:#)?([a-zA-Z0-9_-]+)', message_lower)
            
            if channel_match:
                channel = channel_match.group(1).strip()
            
            # Extract message content
            content = None
            content_match = re.search(r'(?:say|post|send|write|tell)(?:\s+that)?\s+["\']([^"\']+)["\']', message)
            
            if content_match:
                content = content_match.group(1)
            else:
                # Look for message after relevant keywords
                message_keywords = ["saying", "that says", "with message", "with text"]
                for keyword in message_keywords:
                    if keyword in message_lower:
                        keyword_pos = message_lower.find(keyword) + len(keyword)
                        content = message[keyword_pos:].strip()
                        break
            
            if not content:
                # Try to extract everything after the channel
                if channel_match:
                    channel_end_pos = message_lower.find(channel) + len(channel)
                    content = message[channel_end_pos:].strip()
                    
                    # Clean up the content
                    content = re.sub(r'^[,:\s]+', '', content)
            
            if not content:
                return f"What message would you like to send to the '#{channel}' channel on Discord?"
            
            # Send the message (mock implementation)
            timestamp = datetime.now().isoformat()
            self._update_last_message(user_id, timestamp)
            
            server_name = settings.get("server_name", "Discord Server")
            return f"I've sent your message to the #{channel} channel on the '{server_name}' Discord server:\n\n\"{content}\""
        
        # Handle checking statuses
        elif any(cmd in message_lower for cmd in ["check", "status"]):
            server_name = settings.get("server_name", "Discord Server")
            
            # Generate mock notifications
            notifications = self._generate_mock_notifications(3)
            
            if not notifications:
                return "You have no new notifications on Discord."
            
            response = f"Here are your recent notifications from Discord ({server_name}):\n\n"
            
            for notification in notifications:
                response += f"• {notification['sender']} in #{notification['channel']}: \"{notification['message']}\"\n"
                response += f"  {notification['time_ago']} ago\n\n"
            
            return response
        
        # If we get here, no command matched
        return "I couldn't understand your Discord request. You can say things like 'Send a Discord message to #general' or 'Check my Discord notifications'."
    
    def _update_discord_settings(self, user_id: str, server_name: str, default_channel: str, server_id: str = None) -> bool:
        """
        Update Discord settings for a user.
        
        Args:
            user_id: The user ID
            server_name: The Discord server name
            default_channel: The default channel
            server_id: The server ID (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            # Check for existing settings
            c.execute("SELECT * FROM discord_settings WHERE user_id = ?", (user_id,))
            existing = c.fetchone()
            
            if existing:
                # Update existing record
                c.execute('''
                    UPDATE discord_settings
                    SET server_name = ?, default_channel = ?
                    WHERE user_id = ?
                ''', (server_name, default_channel, user_id))
            else:
                # Insert new record
                c.execute('''
                    INSERT INTO discord_settings
                    (user_id, server_name, default_channel, server_id)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, server_name, default_channel, server_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating Discord settings: {e}")
            return False
    
    def _update_last_message(self, user_id: str, timestamp: str) -> bool:
        """
        Update the last message timestamp.
        
        Args:
            user_id: The user ID
            timestamp: The message timestamp
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            c.execute('''
                UPDATE discord_settings
                SET last_message_timestamp = ?
                WHERE user_id = ?
            ''', (timestamp, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating last message timestamp: {e}")
            return False
    
    def _get_discord_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get Discord settings for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            dict: The Discord settings
        """
        try:
            c = self.conn.cursor()
            
            c.execute("SELECT * FROM discord_settings WHERE user_id = ?", (user_id,))
            record = c.fetchone()
            
            if record:
                return {
                    "server_name": record[2],
                    "default_channel": record[3],
                    "server_id": record[4],
                    "last_message_timestamp": record[5],
                    "notification_preferences": record[6]
                }
            
            return {}
        except Exception as e:
            print(f"Error getting Discord settings: {e}")
            return {}
    
    def _generate_mock_notifications(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Generate mock Discord notifications for demonstration purposes.
        
        Args:
            count: The number of notifications to generate
            
        Returns:
            list: A list of notification dictionaries
        """
        if count <= 0:
            return []
        
        notifications = []
        
        # Generate Discord usernames
        usernames = ["GamerPro42", "DiscordMaster", "PixelWizard", "ServerAdmin", "NightOwl", "CodeNinja"]
        
        channels = ["general", "gaming", "music", "memes", "off-topic", "announcements", "help"]
        
        messages = [
            "Anyone up for some gaming tonight?",
            "Check out this new song I found",
            "This meme is hilarious 😂",
            "Server will be down for maintenance at midnight",
            "Need help with this coding problem",
            "New bot commands available!",
            "Who's joining the voice chat?",
            "Movie night this weekend?",
            "Did you see the latest update?",
            "Streaming in 30 minutes, join me!"
        ]
        
        time_frames = [
            "1 minute", "2 minutes", "5 minutes", "10 minutes", "15 minutes", 
            "30 minutes", "1 hour", "2 hours", "3 hours", "4 hours"
        ]
        
        for i in range(count):
            sender = usernames[i % len(usernames)]
            channel = channels[i % len(channels)]
            message = messages[i % len(messages)]
            time_ago = time_frames[i % len(time_frames)]
            
            notifications.append({
                "sender": sender,
                "channel": channel,
                "message": message,
                "time_ago": time_ago
            })
        
        return notifications 