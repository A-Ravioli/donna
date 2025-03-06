import re
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random  # For mock data generation

from .base import BaseIntegration

class UberLyftIntegration(BaseIntegration):
    """Integration for Uber and Lyft ride services."""
    
    def get_name(self) -> str:
        return "Ride Sharing"
    
    def get_commands(self) -> List[str]:
        return [
            "get a ride",
            "call uber",
            "call lyft",
            "book a ride",
            "order a car",
            "get me a taxi",
            "ride to",
            "setup uber",
            "setup lyft",
            "check ride status",
            "cancel ride"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS ride_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            preferred_service TEXT,
            home_address TEXT,
            work_address TEXT,
            last_ride_id TEXT,
            last_ride_status TEXT,
            last_ride_timestamp DATETIME
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
        
        # Check for ride service mentions
        ride_services = ["uber", "lyft", "ride", "taxi", "car service"]
        for service in ride_services:
            if service in message_lower:
                # Look for action indicators
                action_words = ["get", "book", "order", "call", "need", "want", "take"]
                for action in action_words:
                    if action in message_lower:
                        return True
                        
                # Look for destination indicators
                if "to " in message_lower and any(place in message_lower for place in 
                                            ["airport", "station", "downtown", "home", "office", "work", "restaurant"]):
                    return True
        
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Handle setup commands
        if "setup uber" in message_lower or "setup lyft" in message_lower:
            # Determine which service to set up
            service = "Uber" if "uber" in message_lower else "Lyft"
            
            # In a real implementation, we would start an OAuth flow
            # For this example, we'll just save some basic preferences
            
            # Extract addresses if provided
            home_address = None
            work_address = None
            
            home_match = re.search(r'home(?:\s+address)?\s+(?:is|at|:)?\s+([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            work_match = re.search(r'work(?:\s+address)?\s+(?:is|at|:)?\s+([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            
            if home_match:
                home_address = home_match.group(1).strip()
            
            if work_match:
                work_address = work_match.group(1).strip()
            
            # Store credentials (API keys would go here in a real implementation)
            credentials = {
                "service": service.lower(),
                "api_key": "placeholder_api_key",
                "refresh_token": "placeholder_refresh_token",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            if self.store_credentials(user_id, credentials):
                self._update_ride_settings(user_id, service.lower(), home_address, work_address)
                
                response = f"Your {service} account has been set up! "
                if home_address:
                    response += f"I've saved your home address as '{home_address}'. "
                if work_address:
                    response += f"I've saved your work address as '{work_address}'. "
                
                response += f"You can now order rides through Alfred by saying 'Get me an {service}' or 'I need a ride to [destination]'."
                return response
            else:
                return f"There was an error setting up your {service} account. Please try again."
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get user credentials and settings
        credentials = self.get_credentials(user_id)
        preferred_service = credentials.get("service", "uber").lower()
        settings = self._get_ride_settings(user_id)
        
        # Handle ride booking
        if any(cmd in message_lower for cmd in ["get a ride", "call uber", "call lyft", "book a ride", "order a car", "get me a taxi", "ride to"]):
            # Determine which service to use
            service = preferred_service
            if "uber" in message_lower:
                service = "uber"
            elif "lyft" in message_lower:
                service = "lyft"
            
            # Extract destination
            destination = self._extract_destination(message)
            if not destination:
                return "I couldn't determine where you want to go. Please specify a destination, like 'Get me an Uber to the airport'."
            
            # Extract ride type if specified
            ride_type = "standard"  # Default
            luxury_indicators = ["luxury", "black", "premium", "comfort", "xl", "suv", "exec"]
            economy_indicators = ["economy", "pool", "share", "shared", "basic", "standard"]
            
            for indicator in luxury_indicators:
                if indicator in message_lower:
                    ride_type = "premium"
                    break
            
            for indicator in economy_indicators:
                if indicator in message_lower:
                    ride_type = "economy"
                    break
            
            # Extract pickup location (default to current location)
            pickup = "current location"
            pickup_match = re.search(r'from\s+([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            
            if pickup_match:
                pickup = pickup_match.group(1).strip()
            elif "home" in message_lower and settings.get("home_address"):
                pickup = settings.get("home_address")
            elif "work" in message_lower and settings.get("work_address"):
                pickup = settings.get("work_address")
            
            # Extract number of passengers if specified
            passengers = 1  # Default
            passengers_match = re.search(r'(\d+)\s+(?:person|people|passenger)', message_lower)
            
            if passengers_match:
                passengers = int(passengers_match.group(1))
                if passengers > 4 and ride_type != "premium":
                    ride_type = "premium"  # Automatically upgrade for more passengers
            
            # Calculate mock ride details
            ride_details = self._generate_mock_ride(service, ride_type, pickup, destination)
            
            # Save ride information to settings
            self._update_ride_status(
                user_id, 
                ride_details["ride_id"], 
                "booked", 
                ride_details
            )
            
            # Format response
            service_name = service.capitalize()
            
            response = f"I've booked you a {ride_type} {service_name} from {pickup} to {destination}.\n\n"
            response += f"Your driver {ride_details['driver_name']} will arrive in {ride_details['eta']} minutes driving a {ride_details['car_color']} {ride_details['car_model']}.\n"
            response += f"License plate: {ride_details['license_plate']}\n"
            response += f"Estimated fare: ${ride_details['estimated_fare']:.2f}\n"
            response += f"Estimated arrival time: {ride_details['arrival_time']}"
            
            return response
        
        # Handle ride status check
        elif "check ride status" in message_lower:
            # Get the last ride
            last_ride = settings.get("last_ride_status")
            last_ride_details = None
            
            if settings.get("last_ride_details"):
                try:
                    last_ride_details = json.loads(settings.get("last_ride_details"))
                except:
                    last_ride_details = None
            
            if not last_ride or not last_ride_details:
                return "You don't have any active rides at the moment."
            
            # Check how much time has passed
            last_ride_time = datetime.fromisoformat(settings.get("last_ride_timestamp")) if settings.get("last_ride_timestamp") else datetime.now()
            minutes_passed = (datetime.now() - last_ride_time).total_seconds() / 60
            
            # Update status based on time passed
            status = last_ride
            if status == "booked" and minutes_passed > 5:
                status = "on the way"
                self._update_ride_status(user_id, settings.get("last_ride_id"), status)
            elif status == "on the way" and minutes_passed > 15:
                status = "arriving"
                self._update_ride_status(user_id, settings.get("last_ride_id"), status)
            elif status == "arriving" and minutes_passed > 20:
                status = "in progress"
                self._update_ride_status(user_id, settings.get("last_ride_id"), status)
            elif status == "in progress" and minutes_passed > 40:
                status = "completed"
                self._update_ride_status(user_id, settings.get("last_ride_id"), status)
            
            # Format response based on status
            service_name = last_ride_details.get("service", "ride").capitalize()
            
            if status == "booked":
                response = f"Your {service_name} has been booked and is being assigned a driver.\n"
                response += f"Pickup: {last_ride_details.get('pickup')}\n"
                response += f"Destination: {last_ride_details.get('destination')}\n"
                response += f"Estimated fare: ${last_ride_details.get('estimated_fare'):.2f}"
            elif status == "on the way":
                response = f"Your {service_name} driver {last_ride_details.get('driver_name')} is on the way.\n"
                response += f"They're driving a {last_ride_details.get('car_color')} {last_ride_details.get('car_model')} (License: {last_ride_details.get('license_plate')})\n"
                response += f"ETA: {max(1, int(last_ride_details.get('eta')) - int(minutes_passed))} minutes"
            elif status == "arriving":
                response = f"Your {service_name} driver {last_ride_details.get('driver_name')} is arriving now!\n"
                response += f"Look for a {last_ride_details.get('car_color')} {last_ride_details.get('car_model')} with license plate {last_ride_details.get('license_plate')}"
            elif status == "in progress":
                response = f"You're currently on your way to {last_ride_details.get('destination')}.\n"
                response += f"Your {service_name} driver is {last_ride_details.get('driver_name')}.\n"
                eta_minutes = max(1, int(last_ride_details.get('trip_duration', 20)) - int(minutes_passed - 20))
                response += f"ETA to destination: {eta_minutes} minutes"
            elif status == "completed":
                response = f"Your {service_name} ride has been completed.\n"
                response += f"You arrived at {last_ride_details.get('destination')} at approximately {(last_ride_time + timedelta(minutes=40)).strftime('%I:%M %p')}.\n"
                response += f"Final fare: ${last_ride_details.get('estimated_fare'):.2f}"
            else:
                response = f"Your {service_name} ride status is: {status}."
            
            return response
        
        # Handle ride cancellation
        elif "cancel ride" in message_lower:
            last_ride = settings.get("last_ride_status")
            
            if not last_ride or last_ride == "completed":
                return "You don't have any active rides to cancel."
            
            # Check how much time has passed (for cancellation fee logic)
            last_ride_time = datetime.fromisoformat(settings.get("last_ride_timestamp")) if settings.get("last_ride_timestamp") else datetime.now()
            minutes_passed = (datetime.now() - last_ride_time).total_seconds() / 60
            
            # Update status
            self._update_ride_status(user_id, settings.get("last_ride_id"), "cancelled")
            
            # Determine if there's a cancellation fee
            cancellation_fee = 0.0
            if minutes_passed > 2:
                # More than 2 minutes passed, apply cancellation fee
                cancellation_fee = round(random.uniform(3.0, 7.0), 2)
            
            # Format response
            if cancellation_fee > 0:
                return f"Your ride has been cancelled. A cancellation fee of ${cancellation_fee:.2f} will be applied to your account."
            else:
                return "Your ride has been cancelled. No cancellation fee will be charged."
        
        # If we get here, no command matched
        return "I couldn't understand your ride request. You can say things like 'Get me an Uber to the airport' or 'Call a Lyft to 123 Main Street'."
    
    def _extract_destination(self, message: str) -> Optional[str]:
        """
        Extract the destination from a message.
        
        Args:
            message: The message text
            
        Returns:
            str: The destination, or None if not found
        """
        message_lower = message.lower()
        
        # Check for common destination patterns
        to_match = re.search(r'to\s+([^,\.?!]+)(?:[,\.?!]|$)', message_lower)
        if to_match:
            return to_match.group(1).strip()
        
        # Check for named locations
        for place in ["airport", "train station", "bus station", "downtown", "hospital", "mall"]:
            if f"the {place}" in message_lower:
                return f"the {place}"
        
        # Check for home/work
        if "home" in message_lower:
            return "home"
        elif "work" in message_lower or "office" in message_lower:
            return "work"
        
        return None
    
    def _update_ride_settings(self, user_id: str, preferred_service: str, home_address: Optional[str] = None, work_address: Optional[str] = None) -> bool:
        """
        Update ride settings for a user.
        
        Args:
            user_id: The user ID
            preferred_service: The preferred ride service (uber/lyft)
            home_address: The home address (optional)
            work_address: The work address (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            # Get existing settings
            c.execute("SELECT * FROM ride_settings WHERE user_id = ?", (user_id,))
            existing = c.fetchone()
            
            if existing:
                # Update existing record
                if home_address is None:
                    home_address = existing[3]
                if work_address is None:
                    work_address = existing[4]
                
                c.execute('''
                    UPDATE ride_settings
                    SET preferred_service = ?, home_address = ?, work_address = ?
                    WHERE user_id = ?
                ''', (preferred_service, home_address, work_address, user_id))
            else:
                # Insert new record
                c.execute('''
                    INSERT INTO ride_settings
                    (user_id, preferred_service, home_address, work_address)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, preferred_service, home_address, work_address))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating ride settings: {e}")
            return False
    
    def _update_ride_status(self, user_id: str, ride_id: str, status: str, ride_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the status of a ride.
        
        Args:
            user_id: The user ID
            ride_id: The ride ID
            status: The ride status
            ride_details: Optional ride details as a dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            ride_details_json = None
            if ride_details:
                ride_details_json = json.dumps(ride_details)
            
            c.execute('''
                UPDATE ride_settings
                SET last_ride_id = ?, last_ride_status = ?, last_ride_timestamp = ?, last_ride_details = ?
                WHERE user_id = ?
            ''', (ride_id, status, datetime.now().isoformat(), ride_details_json, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating ride status: {e}")
            return False
    
    def _get_ride_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get ride settings for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            dict: The ride settings
        """
        try:
            c = self.conn.cursor()
            
            c.execute("SELECT * FROM ride_settings WHERE user_id = ?", (user_id,))
            record = c.fetchone()
            
            if record:
                return {
                    "preferred_service": record[2],
                    "home_address": record[3],
                    "work_address": record[4],
                    "last_ride_id": record[5],
                    "last_ride_status": record[6],
                    "last_ride_timestamp": record[7],
                    "last_ride_details": record[8] if len(record) > 8 else None
                }
            
            return {}
        except Exception as e:
            print(f"Error getting ride settings: {e}")
            return {}
    
    def _generate_mock_ride(self, service: str, ride_type: str, pickup: str, destination: str) -> Dict[str, Any]:
        """
        Generate mock ride details for demonstration purposes.
        
        Args:
            service: The ride service (uber/lyft)
            ride_type: The type of ride (economy/standard/premium)
            pickup: The pickup location
            destination: The destination
            
        Returns:
            dict: Mock ride details
        """
        # Generate a random ride ID
        ride_id = f"{service[0].upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Generate a random driver name
        first_names = ["Michael", "Sarah", "David", "Jessica", "John", "Emily", "Robert", "Jennifer", "William", "Emma"]
        last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        driver_name = f"{random.choice(first_names)} {random.choice(last_names)[0]}."
        
        # Generate a random car model
        car_models = {
            "economy": ["Toyota Prius", "Honda Civic", "Hyundai Elantra", "Nissan Sentra", "Kia Rio"],
            "standard": ["Toyota Camry", "Honda Accord", "Mazda 6", "Chevrolet Malibu", "Ford Fusion"],
            "premium": ["BMW 5 Series", "Mercedes E-Class", "Audi A6", "Lexus ES", "Cadillac CTS"]
        }
        
        car_model = random.choice(car_models.get(ride_type, car_models["standard"]))
        
        # Generate a random car color
        car_colors = ["Black", "White", "Silver", "Gray", "Blue", "Red"]
        car_color = random.choice(car_colors)
        
        # Generate a random license plate
        license_letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))
        license_numbers = "".join(random.choices("0123456789", k=3))
        license_plate = f"{license_letters} {license_numbers}"
        
        # Generate ETA, fare, and other details
        eta = random.randint(3, 15)  # minutes
        
        base_fare = {
            "economy": random.uniform(10.0, 15.0),
            "standard": random.uniform(15.0, 25.0),
            "premium": random.uniform(30.0, 60.0)
        }
        
        estimated_fare = base_fare.get(ride_type, base_fare["standard"])
        
        # Add random surge if busy time
        if random.random() < 0.3:  # 30% chance of surge
            surge_multiplier = random.uniform(1.2, 2.0)
            estimated_fare *= surge_multiplier
        
        # Round fare to nearest 49 cents for marketing psychology
        estimated_fare = round(estimated_fare * 2) / 2 - 0.01
        
        # Calculate trip duration and arrival time
        trip_duration = random.randint(10, 40)  # minutes
        arrival_time = (datetime.now() + timedelta(minutes=eta+trip_duration)).strftime("%I:%M %p")
        
        return {
            "service": service,
            "ride_id": ride_id,
            "ride_type": ride_type,
            "driver_name": driver_name,
            "car_model": car_model,
            "car_color": car_color,
            "license_plate": license_plate,
            "eta": eta,
            "pickup": pickup,
            "destination": destination,
            "estimated_fare": estimated_fare,
            "trip_duration": trip_duration,
            "arrival_time": arrival_time
        } 