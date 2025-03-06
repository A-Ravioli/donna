import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests

from .base import BaseIntegration

class CalendarIntegration(BaseIntegration):
    """Integration for managing calendars."""
    
    def get_name(self) -> str:
        return "Calendar"
    
    def get_commands(self) -> List[str]:
        return [
            "schedule meeting",
            "create event",
            "add event",
            "check calendar",
            "show events",
            "upcoming events",
            "list appointments",
            "setup calendar"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS calendar_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            calendar_type TEXT,
            primary_calendar_id TEXT,
            last_sync DATETIME
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
                
        # Also check for common calendar-related phrases
        calendar_phrases = [
            "schedule",
            "appointment",
            "meeting",
            "my calendar",
            "events",
            "what do i have",
            "am i free"
        ]
        
        # Check both exact matches and sentence context
        for phrase in calendar_phrases:
            if phrase in message_lower:
                # Make sure this is actually a calendar request
                # For example "am i free" could be about many things
                time_indicators = [
                    "today", "tomorrow", "next week", "on monday", "at 2", "this afternoon",
                    "this evening", "tonight", "january", "february", "march", "april",
                    "may", "june", "july", "august", "september", "october", "november",
                    "december"
                ]
                
                for indicator in time_indicators:
                    if indicator in message_lower:
                        return True
                        
                calendar_context = [
                    "calendar", "schedule", "free time", "availability", "busy",
                    "event", "appointment", "meeting", "reminder"
                ]
                
                for context in calendar_context:
                    if context in message_lower:
                        return True
        
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Handle setup command
        if "setup calendar" in message_lower:
            # For this example, we'll assume OAuth would be handled elsewhere
            # and we're just setting a preference for calendar type
            
            # Extract calendar type from the message
            calendar_type = None
            
            if "google" in message_lower:
                calendar_type = "google"
            elif "outlook" in message_lower or "microsoft" in message_lower:
                calendar_type = "outlook"
            elif "apple" in message_lower or "icloud" in message_lower:
                calendar_type = "apple"
            else:
                return "Please specify which calendar service you want to use (Google, Outlook, or Apple)."
            
            # In a real system, here we would start an OAuth flow to get access tokens
            # For this example, we'll just save the preference
            
            # Store a placeholder for credentials
            credentials = {
                "calendar_type": calendar_type,
                "auth_token": "placeholder_token",  # In a real system, this would be a real token
                "refresh_token": "placeholder_refresh_token",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            if self.store_credentials(user_id, credentials):
                self._update_calendar_settings(user_id, calendar_type)
                return f"Your {calendar_type.capitalize()} Calendar has been set up! You can now schedule meetings and check your calendar through Alfred."
            else:
                return f"There was an error setting up your {calendar_type.capitalize()} Calendar. Please try again."
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get the user's credentials
        credentials = self.get_credentials(user_id)
        calendar_type = credentials.get("calendar_type", "google")  # Default to Google if not specified
        
        # Mock calendar data for demonstration purposes
        # In a real system, this would come from the calendar API
        
        # Handle event creation
        if any(cmd in message_lower for cmd in ["schedule meeting", "create event", "add event"]):
            # Extract event details using regex
            title_match = re.search(r'(?:called|titled|about|for|with subject)\s+["\']?([^"\']+)["\']?', message)
            date_match = re.search(r'(?:on|for)\s+([a-zA-Z]+\s+\d+(?:st|nd|rd|th)?|\d+(?:st|nd|rd|th)?\s+[a-zA-Z]+|\d{1,2}/\d{1,2}(?:/\d{2,4})?|tomorrow|today|next [a-zA-Z]+)', message)
            time_match = re.search(r'(?:at|from)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?(?:\s*-\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)', message)
            duration_match = re.search(r'for\s+(\d+)\s+(hour|minute)s?', message)
            attendees_match = re.search(r'with\s+([^,\.]+(?:,\s*[^,\.]+)*)', message)
            
            # Extract event title
            title = "New Event"
            if title_match:
                title = title_match.group(1).strip()
            
            # Extract date
            event_date = datetime.now().date()
            if date_match:
                date_str = date_match.group(1).lower()
                
                if "tomorrow" in date_str:
                    event_date = (datetime.now() + timedelta(days=1)).date()
                elif "today" in date_str:
                    event_date = datetime.now().date()
                elif "next" in date_str:
                    # Handle "next Monday", "next week", etc.
                    if "week" in date_str:
                        event_date = (datetime.now() + timedelta(days=7)).date()
                    else:
                        # Try to extract day of week
                        day_of_week = date_str.replace("next", "").strip()
                        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                        
                        if day_of_week in days:
                            today = datetime.now().weekday()
                            target_day = days.index(day_of_week)
                            days_ahead = (target_day - today) % 7
                            if days_ahead == 0:
                                days_ahead = 7  # If today is the target day, go to next week
                                
                            event_date = (datetime.now() + timedelta(days=days_ahead)).date()
                else:
                    # Try to parse as MM/DD or MM/DD/YYYY
                    if "/" in date_str:
                        parts = date_str.split("/")
                        if len(parts) == 2:
                            month, day = parts
                            year = datetime.now().year
                        else:
                            month, day, year = parts
                            if len(year) == 2:
                                year = "20" + year
                                
                        event_date = datetime(int(year), int(month), int(day)).date()
            
            # Extract time
            event_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0).time()
            event_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).time()
            
            if time_match:
                time_str = time_match.group(1).lower()
                
                # Check if it's a range (e.g., "9am-10am")
                if "-" in time_str:
                    start_time_str, end_time_str = time_str.split("-")
                    
                    # Parse start time
                    start_time_str = start_time_str.strip()
                    start_hour, start_minute = self._parse_time(start_time_str)
                    event_time = datetime.now().replace(hour=start_hour, minute=start_minute, second=0, microsecond=0).time()
                    
                    # Parse end time
                    end_time_str = end_time_str.strip()
                    end_hour, end_minute = self._parse_time(end_time_str)
                    event_end_time = datetime.now().replace(hour=end_hour, minute=end_minute, second=0, microsecond=0).time()
                else:
                    # Just a start time, calculate end time based on duration
                    hour, minute = self._parse_time(time_str)
                    event_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()
                    
                    # Default to 1 hour meeting
                    duration_hours = 1
                    
                    # Override if duration is specified
                    if duration_match:
                        duration_amount = int(duration_match.group(1))
                        duration_unit = duration_match.group(2)
                        
                        if duration_unit == "hour":
                            duration_hours = duration_amount
                        else:  # minutes
                            duration_hours = duration_amount / 60
                    
                    # Calculate end time
                    start_datetime = datetime.combine(event_date, event_time)
                    end_datetime = start_datetime + timedelta(hours=duration_hours)
                    event_end_time = end_datetime.time()
            
            # Extract attendees
            attendees = []
            if attendees_match:
                attendees_str = attendees_match.group(1)
                
                # Extract email addresses
                email_matches = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', attendees_str)
                attendees.extend(email_matches)
                
                # Add other names as potential attendees
                if not email_matches:
                    for name in attendees_str.split(","):
                        name = name.strip()
                        if name and "and" not in name.lower():
                            attendees.append(name)
            
            # Create a mock event (in a real system, we would call the calendar API)
            event = {
                "title": title,
                "date": event_date.strftime("%Y-%m-%d"),
                "start_time": event_time.strftime("%H:%M"),
                "end_time": event_end_time.strftime("%H:%M"),
                "attendees": attendees
            }
            
            # In a real system, we would save this to the calendar API
            # Here, we'll just return a confirmation message
            start_datetime = datetime.combine(event_date, event_time)
            end_datetime = datetime.combine(event_date, event_end_time)
            
            response = f"I've scheduled \"{title}\" on {start_datetime.strftime('%A, %B %d')} from {start_datetime.strftime('%I:%M %p')} to {end_datetime.strftime('%I:%M %p')}."
            
            if attendees:
                response += f" Attendees: {', '.join(attendees)}."
                
            return response
        
        # Handle calendar check
        elif any(cmd in message_lower for cmd in ["check calendar", "show events", "upcoming events", "list appointments"]):
            # Extract date range
            date_range = "today"
            
            if "tomorrow" in message_lower:
                date_range = "tomorrow"
            elif "week" in message_lower:
                date_range = "week"
            elif "month" in message_lower:
                date_range = "month"
            
            # Generate mock events (in a real system, this would come from the calendar API)
            events = self._get_mock_events(date_range)
            
            if not events:
                if date_range == "today":
                    return "You don't have any events scheduled for today."
                elif date_range == "tomorrow":
                    return "You don't have any events scheduled for tomorrow."
                elif date_range == "week":
                    return "You don't have any events scheduled for this week."
                else:
                    return "You don't have any upcoming events scheduled."
            
            # Format events for display
            if date_range == "today":
                response = "Here are your events for today:\n\n"
            elif date_range == "tomorrow":
                response = "Here are your events for tomorrow:\n\n"
            elif date_range == "week":
                response = "Here are your events for this week:\n\n"
            else:
                response = "Here are your upcoming events:\n\n"
            
            for event in events:
                response += f"• {event['start_time']} - {event['end_time']}: {event['title']}"
                
                if event.get("location"):
                    response += f" at {event['location']}"
                    
                if event.get("attendees"):
                    response += f" with {', '.join(event['attendees'])}"
                    
                response += "\n"
            
            return response
        
        # If we get here, no command matched
        return "I didn't understand your calendar request. You can say 'schedule a meeting', 'create an event', or 'check my calendar'."
    
    def _update_calendar_settings(self, user_id: str, calendar_type: str) -> bool:
        """
        Update calendar settings for a user.
        
        Args:
            user_id: The ID of the user
            calendar_type: The type of calendar
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO calendar_settings
                (user_id, calendar_type, last_sync)
                VALUES (?, ?, ?)
            ''', (user_id, calendar_type, datetime.now().isoformat()))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating calendar settings: {e}")
            return False
    
    def _parse_time(self, time_str: str) -> (int, int):
        """
        Parse a time string into hours and minutes.
        
        Args:
            time_str: The time string (e.g., "9am", "3:30pm")
            
        Returns:
            tuple: (hour, minute)
        """
        # Check if it's in 12-hour format with am/pm
        if "am" in time_str or "pm" in time_str:
            # Split at colon if present
            if ":" in time_str:
                time_parts = time_str.replace("am", "").replace("pm", "").strip().split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1])
            else:
                hour = int(time_str.replace("am", "").replace("pm", "").strip())
                minute = 0
            
            # Adjust for PM
            if "pm" in time_str and hour < 12:
                hour += 12
            
            # Adjust for 12 AM
            if "am" in time_str and hour == 12:
                hour = 0
        else:
            # Assume 24-hour format
            if ":" in time_str:
                time_parts = time_str.strip().split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1])
            else:
                hour = int(time_str.strip())
                minute = 0
        
        return hour, minute
    
    def _get_mock_events(self, date_range: str) -> List[Dict[str, Any]]:
        """
        Get mock events for demonstration purposes.
        
        Args:
            date_range: The date range ("today", "tomorrow", "week", "month")
            
        Returns:
            list: A list of event dictionaries
        """
        # Generate realistic mock events
        now = datetime.now()
        
        if date_range == "today":
            # No events 20% of the time
            if now.second % 5 == 0:
                return []
                
            # 1-3 events for today
            count = (now.second % 3) + 1
            
            events = []
            for i in range(count):
                hour = 9 + i * 2  # Spread throughout the day
                
                events.append({
                    "title": self._get_mock_event_title(),
                    "date": now.strftime("%Y-%m-%d"),
                    "start_time": f"{hour}:00",
                    "end_time": f"{hour + 1}:00",
                    "location": self._get_mock_location() if i % 2 == 0 else None,
                    "attendees": self._get_mock_attendees() if i % 3 == 0 else None
                })
                
            return events
        elif date_range == "tomorrow":
            # No events 30% of the time
            if now.second % 10 < 3:
                return []
                
            # 1-2 events for tomorrow
            count = (now.second % 2) + 1
            tomorrow = now + timedelta(days=1)
            
            events = []
            for i in range(count):
                hour = 10 + i * 3  # Spread throughout the day
                
                events.append({
                    "title": self._get_mock_event_title(),
                    "date": tomorrow.strftime("%Y-%m-%d"),
                    "start_time": f"{hour}:00",
                    "end_time": f"{hour + 1}:30",
                    "location": self._get_mock_location() if i % 2 == 0 else None,
                    "attendees": self._get_mock_attendees() if i % 3 == 0 else None
                })
                
            return events
        elif date_range == "week":
            # Generate 3-7 events for the week
            count = (now.second % 5) + 3
            
            events = []
            for i in range(count):
                day_offset = i % 7  # Spread throughout the week
                event_date = now + timedelta(days=day_offset)
                hour = 9 + (i * 97) % 8  # Somewhat random hours
                
                events.append({
                    "title": self._get_mock_event_title(),
                    "date": event_date.strftime("%Y-%m-%d"),
                    "start_time": f"{hour}:00",
                    "end_time": f"{hour + 1}:00",
                    "location": self._get_mock_location() if i % 2 == 0 else None,
                    "attendees": self._get_mock_attendees() if i % 3 == 0 else None
                })
                
            return events
        else:
            # Generate 5-10 events for the month
            count = (now.second % 6) + 5
            
            events = []
            for i in range(count):
                day_offset = (i * 3) % 30  # Spread throughout the month
                event_date = now + timedelta(days=day_offset)
                hour = 9 + (i * 97) % 8  # Somewhat random hours
                
                events.append({
                    "title": self._get_mock_event_title(),
                    "date": event_date.strftime("%Y-%m-%d"),
                    "start_time": f"{hour}:00",
                    "end_time": f"{hour + 1}:00",
                    "location": self._get_mock_location() if i % 2 == 0 else None,
                    "attendees": self._get_mock_attendees() if i % 3 == 0 else None
                })
                
            return events
    
    def _get_mock_event_title(self) -> str:
        """Get a mock event title."""
        titles = [
            "Team Meeting",
            "Project Review",
            "Client Call",
            "Strategy Session",
            "Lunch with Team",
            "Product Demo",
            "Weekly Update",
            "Budget Planning",
            "Marketing Review",
            "HR Interview",
            "1:1 with Manager",
            "Design Review",
            "Code Review",
            "Sprint Planning",
            "Customer Meeting"
        ]
        
        return titles[datetime.now().second % len(titles)]
    
    def _get_mock_location(self) -> str:
        """Get a mock location."""
        locations = [
            "Conference Room A",
            "Zoom Meeting",
            "Google Meet",
            "Office",
            "Coffee Shop",
            "Main Street Office",
            "Client HQ",
            "Virtual",
            "Phone Call"
        ]
        
        return locations[datetime.now().second % len(locations)]
    
    def _get_mock_attendees(self) -> List[str]:
        """Get mock attendees."""
        all_attendees = [
            "john@example.com",
            "sarah@example.com",
            "team@company.com",
            "client@client.com",
            "manager@company.com",
            "alex@team.com"
        ]
        
        # Pick 1-3 random attendees
        count = (datetime.now().second % 3) + 1
        start_idx = datetime.now().second % len(all_attendees)
        
        return all_attendees[start_idx:start_idx + count] 