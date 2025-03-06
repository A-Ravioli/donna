import re
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base import BaseIntegration

class FoodDeliveryIntegration(BaseIntegration):
    """Integration for food delivery services like DoorDash, UberEats, etc."""
    
    def get_name(self) -> str:
        return "Food Delivery"
    
    def get_commands(self) -> List[str]:
        return [
            "order food", 
            "get delivery",
            "order from",
            "doordash",
            "ubereats",
            "grubhub",
            "get takeout",
            "deliver food",
            "setup food delivery",
            "check food order",
            "track order",
            "cancel food order"
        ]
    
    def get_table_schema(self) -> Optional[str]:
        return '''
        CREATE TABLE IF NOT EXISTS food_delivery_settings (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE,
            preferred_service TEXT,
            default_address TEXT,
            favorite_restaurants TEXT,
            last_order_id TEXT,
            last_order_status TEXT,
            last_order_timestamp DATETIME,
            last_order_details TEXT
        )
        '''
    
    def can_handle(self, message: str) -> bool:
        message_lower = message.lower()
        
        # Check if any command matches
        for command in self.get_commands():
            if command in message_lower:
                return True
        
        # Check for food delivery keywords
        food_services = ["doordash", "ubereats", "grubhub", "postmates", "delivery", "takeout"]
        food_keywords = ["pizza", "burger", "sushi", "chinese", "mexican", "indian", "thai", "italian", "food"]
        
        # Check for service mentions
        for service in food_services:
            if service in message_lower:
                return True
        
        # Check for combinations of ordering actions and food
        order_words = ["order", "get", "deliver", "bring", "send", "want"]
        for order in order_words:
            if order in message_lower:
                for food in food_keywords:
                    if food in message_lower:
                        return True
        
        return False
    
    def process(self, user_id: str, message: str, **kwargs) -> str:
        message_lower = message.lower()
        
        # Handle setup command
        if "setup food delivery" in message_lower:
            # Extract preferred service if specified
            service = "doordash"  # Default
            
            if "ubereats" in message_lower:
                service = "ubereats"
            elif "grubhub" in message_lower:
                service = "grubhub"
            elif "postmates" in message_lower:
                service = "postmates"
            
            # Extract delivery address if provided
            delivery_address = None
            address_match = re.search(r'address(?:\s+is)?\s+([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            
            if address_match:
                delivery_address = address_match.group(1).strip()
            
            # Extract favorite restaurants if provided
            favorite_restaurants = []
            favorites_match = re.search(r'favorite(?:s)?\s+(?:(?:is|are|include)\s+)?([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            
            if favorites_match:
                favorites_str = favorites_match.group(1)
                for restaurant in favorites_str.split(","):
                    restaurant = restaurant.strip()
                    if restaurant and "and" not in restaurant.lower():
                        favorite_restaurants.append(restaurant)
                    elif "and" in restaurant.lower():
                        parts = restaurant.split("and")
                        for part in parts:
                            part = part.strip()
                            if part:
                                favorite_restaurants.append(part)
            
            # Store credentials (API keys would go here in a real implementation)
            credentials = {
                "service": service,
                "api_key": "placeholder_api_key",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            if self.store_credentials(user_id, credentials):
                self._update_food_settings(
                    user_id, 
                    service, 
                    delivery_address, 
                    favorite_restaurants
                )
                
                response = f"Your {service.capitalize()} account has been set up! "
                if delivery_address:
                    response += f"I've saved your delivery address as '{delivery_address}'. "
                if favorite_restaurants:
                    response += f"Your favorite restaurants: {', '.join(favorite_restaurants)}. "
                
                response += f"You can now order food through Alfred by saying 'Order food from [restaurant]' or 'Get me some pizza'."
                return response
            else:
                return f"There was an error setting up your {service.capitalize()} account. Please try again."
        
        # Check if the user is authenticated
        if not self.is_authenticated(user_id):
            return self.get_authentication_instructions()
        
        # Get user credentials and settings
        credentials = self.get_credentials(user_id)
        preferred_service = credentials.get("service", "doordash").lower()
        settings = self._get_food_settings(user_id)
        
        # Handle food ordering
        if any(cmd in message_lower for cmd in ["order food", "get delivery", "order from", "get takeout", "deliver food"]):
            # Determine which service to use
            service = preferred_service
            for known_service in ["doordash", "ubereats", "grubhub", "postmates"]:
                if known_service in message_lower:
                    service = known_service
                    break
            
            # Extract restaurant name
            restaurant = self._extract_restaurant(message, settings.get("favorite_restaurants", ""))
            if not restaurant:
                return "I couldn't determine which restaurant you want to order from. Please specify, like 'Order food from Pizza Palace'."
            
            # Extract food items
            food_items = self._extract_food_items(message)
            if not food_items:
                return f"What would you like to order from {restaurant}? Please specify some items."
            
            # Extract delivery address (default to saved address)
            delivery_address = settings.get("default_address", "home")
            address_match = re.search(r'to\s+([^,\.]+(?:,\s*[^,\.]+)*)', message_lower)
            
            if address_match:
                delivery_address = address_match.group(1).strip()
            
            # Create mock order
            order_details = self._generate_mock_order(service, restaurant, food_items, delivery_address)
            
            # Save order information
            self._update_order_status(
                user_id, 
                order_details["order_id"], 
                "placed", 
                order_details
            )
            
            # Format response
            service_name = service.capitalize()
            
            response = f"I've placed your {service_name} order with {restaurant}.\n\n"
            response += "Your order:\n"
            
            for item in order_details["items"]:
                response += f"• {item['quantity']}x {item['name']} - ${item['price']:.2f}\n"
            
            response += f"\nSubtotal: ${order_details['subtotal']:.2f}\n"
            response += f"Delivery Fee: ${order_details['delivery_fee']:.2f}\n"
            response += f"Tax: ${order_details['tax']:.2f}\n"
            response += f"Total: ${order_details['total']:.2f}\n\n"
            
            response += f"Estimated delivery time: {order_details['delivery_time']}\n"
            response += f"Delivery to: {order_details['delivery_address']}"
            
            return response
        
        # Handle order tracking
        elif any(cmd in message_lower for cmd in ["check food order", "track order"]):
            # Get the last order
            last_order = settings.get("last_order_status")
            last_order_details = None
            
            if settings.get("last_order_details"):
                try:
                    last_order_details = json.loads(settings.get("last_order_details"))
                except:
                    last_order_details = None
            
            if not last_order or not last_order_details:
                return "You don't have any active food orders at the moment."
            
            # Check how much time has passed
            last_order_time = datetime.fromisoformat(settings.get("last_order_timestamp")) if settings.get("last_order_timestamp") else datetime.now()
            minutes_passed = (datetime.now() - last_order_time).total_seconds() / 60
            
            # Update status based on time passed
            status = last_order
            if status == "placed" and minutes_passed > 3:
                status = "confirmed"
                self._update_order_status(user_id, settings.get("last_order_id"), status)
            elif status == "confirmed" and minutes_passed > 8:
                status = "preparing"
                self._update_order_status(user_id, settings.get("last_order_id"), status)
            elif status == "preparing" and minutes_passed > 20:
                status = "out for delivery"
                self._update_order_status(user_id, settings.get("last_order_id"), status)
            elif status == "out for delivery" and minutes_passed > 35:
                status = "delivered"
                self._update_order_status(user_id, settings.get("last_order_id"), status)
            
            # Format response based on status
            service_name = last_order_details.get("service", "delivery").capitalize()
            restaurant = last_order_details.get("restaurant", "the restaurant")
            
            if status == "placed":
                response = f"Your {service_name} order has been placed with {restaurant}.\n\n"
                response += "We're waiting for the restaurant to confirm your order.\n"
                response += f"Estimated delivery time: {last_order_details.get('delivery_time')}"
            elif status == "confirmed":
                response = f"Your {service_name} order from {restaurant} has been confirmed!\n\n"
                response += "The restaurant has received your order and will start preparing it soon.\n"
                response += f"Estimated delivery time: {last_order_details.get('delivery_time')}"
            elif status == "preparing":
                response = f"Your {service_name} order from {restaurant} is being prepared right now.\n\n"
                eta_minutes = self._get_eta_minutes(last_order_details, minutes_passed)
                response += f"Estimated delivery in about {eta_minutes} minutes."
            elif status == "out for delivery":
                response = f"Your {service_name} order from {restaurant} is out for delivery!\n\n"
                eta_minutes = max(1, int(35 - (minutes_passed - 20)))
                response += f"Your food should arrive in approximately {eta_minutes} minutes.\n"
                response += f"Delivery address: {last_order_details.get('delivery_address')}"
            elif status == "delivered":
                response = f"Your {service_name} order from {restaurant} has been delivered!\n\n"
                response += f"It was delivered to {last_order_details.get('delivery_address')} at around {(last_order_time + timedelta(minutes=35)).strftime('%I:%M %p')}.\n"
                response += "Enjoy your meal! 🍽️"
            else:
                response = f"Your {service_name} order status is: {status}."
            
            return response
        
        # Handle order cancellation
        elif "cancel food order" in message_lower:
            last_order = settings.get("last_order_status")
            
            if not last_order or last_order == "delivered":
                return "You don't have any active food orders to cancel."
            
            # Check if order can be cancelled
            last_order_time = datetime.fromisoformat(settings.get("last_order_timestamp")) if settings.get("last_order_timestamp") else datetime.now()
            minutes_passed = (datetime.now() - last_order_time).total_seconds() / 60
            
            if minutes_passed > 5 and last_order != "placed":
                return "Sorry, your order is already being prepared and can't be cancelled."
            
            # Update status
            self._update_order_status(user_id, settings.get("last_order_id"), "cancelled")
            
            # Format response
            return "Your food order has been cancelled. You won't be charged for this order."
        
        # If we get here, no command matched
        return "I couldn't understand your food delivery request. You can say things like 'Order pizza from Dominos' or 'Get me some sushi'."
    
    def _extract_restaurant(self, message: str, favorites: str = "") -> Optional[str]:
        """
        Extract the restaurant name from a message.
        
        Args:
            message: The message text
            favorites: Comma-separated list of favorite restaurants
            
        Returns:
            str: The restaurant name, or None if not found
        """
        message_lower = message.lower()
        
        # Check for direct mentions
        from_match = re.search(r'from\s+([^,\.?!]+)(?:[,\.?!]|$)', message_lower)
        if from_match:
            return from_match.group(1).strip()
        
        at_match = re.search(r'at\s+([^,\.?!]+)(?:[,\.?!]|$)', message_lower)
        if at_match:
            return at_match.group(1).strip()
        
        # Check for common restaurant chains
        chains = [
            "mcdonalds", "burger king", "wendys", "taco bell", "chipotle", 
            "subway", "dominos", "pizza hut", "papa johns", "kfc", 
            "panda express", "olive garden", "applebees", "chilis", "outback",
            "red lobster", "cheesecake factory", "five guys", "shake shack",
            "popeyes", "chick-fil-a", "panera", "starbucks"
        ]
        
        for chain in chains:
            if chain in message_lower:
                return chain.title()
        
        # Check favorite restaurants if provided
        if favorites:
            favorite_list = [f.strip() for f in favorites.split(",")]
            for favorite in favorite_list:
                if favorite.lower() in message_lower:
                    return favorite
        
        # Check for food types and suggest a restaurant
        food_types = {
            "pizza": ["Pizza Hut", "Dominos", "Papa Johns", "Local Pizza Place"],
            "burger": ["McDonalds", "Burger King", "Five Guys", "Shake Shack"],
            "chinese": ["Panda Express", "China Garden", "Golden Dragon"],
            "sushi": ["Sushi Paradise", "Tokyo Sushi", "Sakura Sushi"],
            "mexican": ["Taco Bell", "Chipotle", "El Pollo Loco", "Local Taqueria"],
            "italian": ["Olive Garden", "Local Italian Restaurant", "Pasta Place"],
            "indian": ["Taste of India", "Curry House", "Spice Garden"],
            "thai": ["Thai Spice", "Bangkok Kitchen", "Thai Smile"]
        }
        
        for food_type, restaurants in food_types.items():
            if food_type in message_lower:
                return random.choice(restaurants)
        
        return None
    
    def _extract_food_items(self, message: str) -> List[Dict[str, Any]]:
        """
        Extract food items from a message.
        
        Args:
            message: The message text
            
        Returns:
            list: A list of food items with quantity and name
        """
        message_lower = message.lower()
        
        # Try to find explicit items (e.g., 2 pizzas, 3 burgers)
        explicit_items = re.findall(r'(\d+)\s+([a-zA-Z\s]+?)(?:,|and|$|\s+with)', message_lower)
        
        if explicit_items:
            return [{"quantity": int(quantity), "name": name.strip()} for quantity, name in explicit_items]
        
        # Check for common food items
        common_items = [
            "pizza", "burger", "fries", "salad", "pasta", "sandwich", "wings", 
            "taco", "burrito", "bowl", "sushi", "roll", "curry", "rice", "noodles",
            "chicken", "steak", "fish", "shrimp", "dessert"
        ]
        
        # Find any mentioned food items
        found_items = []
        for item in common_items:
            if item in message_lower:
                # Try to extract quantity
                quantity_match = re.search(r'(\d+)\s+' + item, message_lower)
                if quantity_match:
                    quantity = int(quantity_match.group(1))
                else:
                    quantity = 1
                
                found_items.append({"quantity": quantity, "name": item.capitalize()})
        
        if found_items:
            return found_items
        
        # If nothing specific is found, infer based on restaurant type or food type
        if "pizza" in message_lower:
            return [{"quantity": 1, "name": "Large Pizza"}]
        elif "burger" in message_lower:
            return [{"quantity": 1, "name": "Burger"}, {"quantity": 1, "name": "Fries"}]
        elif "sushi" in message_lower:
            return [{"quantity": 1, "name": "Sushi Combo"}]
        elif "chinese" in message_lower:
            return [{"quantity": 1, "name": "General Tso's Chicken"}, {"quantity": 1, "name": "Fried Rice"}]
        elif "mexican" in message_lower:
            return [{"quantity": 2, "name": "Tacos"}, {"quantity": 1, "name": "Chips & Salsa"}]
        elif "breakfast" in message_lower:
            return [{"quantity": 1, "name": "Breakfast Combo"}]
        elif "lunch" in message_lower:
            return [{"quantity": 1, "name": "Lunch Special"}]
        elif "dinner" in message_lower:
            return [{"quantity": 1, "name": "Dinner Entree"}]
        
        # Generic food order
        return [{"quantity": 1, "name": "Food Order"}]
    
    def _update_food_settings(self, user_id: str, preferred_service: str, default_address: Optional[str] = None, favorite_restaurants: Optional[List[str]] = None) -> bool:
        """
        Update food delivery settings for a user.
        
        Args:
            user_id: The user ID
            preferred_service: The preferred food delivery service
            default_address: The default delivery address (optional)
            favorite_restaurants: List of favorite restaurants (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            # Get existing settings
            c.execute("SELECT * FROM food_delivery_settings WHERE user_id = ?", (user_id,))
            existing = c.fetchone()
            
            # Prepare favorite restaurants string
            favorites_str = ""
            if favorite_restaurants and len(favorite_restaurants) > 0:
                favorites_str = ",".join(favorite_restaurants)
            
            if existing:
                # Update existing record
                if default_address is None:
                    default_address = existing[3]
                if not favorites_str and existing[4]:
                    favorites_str = existing[4]
                
                c.execute('''
                    UPDATE food_delivery_settings
                    SET preferred_service = ?, default_address = ?, favorite_restaurants = ?
                    WHERE user_id = ?
                ''', (preferred_service, default_address, favorites_str, user_id))
            else:
                # Insert new record
                c.execute('''
                    INSERT INTO food_delivery_settings
                    (user_id, preferred_service, default_address, favorite_restaurants)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, preferred_service, default_address, favorites_str))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating food delivery settings: {e}")
            return False
    
    def _update_order_status(self, user_id: str, order_id: str, status: str, order_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the status of a food order.
        
        Args:
            user_id: The user ID
            order_id: The order ID
            status: The order status
            order_details: Optional order details as a dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            
            order_details_json = None
            if order_details:
                order_details_json = json.dumps(order_details)
            
            c.execute('''
                UPDATE food_delivery_settings
                SET last_order_id = ?, last_order_status = ?, last_order_timestamp = ?, last_order_details = ?
                WHERE user_id = ?
            ''', (order_id, status, datetime.now().isoformat(), order_details_json, user_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating order status: {e}")
            return False
    
    def _get_food_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get food delivery settings for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            dict: The food delivery settings
        """
        try:
            c = self.conn.cursor()
            
            c.execute("SELECT * FROM food_delivery_settings WHERE user_id = ?", (user_id,))
            record = c.fetchone()
            
            if record:
                return {
                    "preferred_service": record[2],
                    "default_address": record[3],
                    "favorite_restaurants": record[4],
                    "last_order_id": record[5],
                    "last_order_status": record[6],
                    "last_order_timestamp": record[7],
                    "last_order_details": record[8] if len(record) > 8 else None
                }
            
            return {}
        except Exception as e:
            print(f"Error getting food delivery settings: {e}")
            return {}
    
    def _get_eta_minutes(self, order_details: Dict[str, Any], minutes_passed: float) -> int:
        """
        Calculate the estimated time until delivery.
        
        Args:
            order_details: The order details dictionary
            minutes_passed: Minutes passed since the order was placed
            
        Returns:
            int: Estimated minutes until delivery
        """
        # Extract the delivery time string
        delivery_time_str = order_details.get("delivery_time", "")
        
        # Try to parse the time
        delivery_time_match = re.search(r'(\d+)[:-](\d+)\s*(am|pm)', delivery_time_str.lower())
        if delivery_time_match:
            hour = int(delivery_time_match.group(1))
            minute = int(delivery_time_match.group(2))
            am_pm = delivery_time_match.group(3)
            
            if am_pm == "pm" and hour < 12:
                hour += 12
            elif am_pm == "am" and hour == 12:
                hour = 0
            
            # Create delivery time
            delivery_time = datetime.now().replace(hour=hour, minute=minute)
            
            # If the delivery time is earlier than now, assume it's for tomorrow
            if delivery_time < datetime.now():
                delivery_time = delivery_time + timedelta(days=1)
            
            # Calculate minutes until delivery
            delta = delivery_time - datetime.now()
            return max(1, int(delta.total_seconds() / 60))
        
        # If we can't parse, use default estimates based on order progress
        if minutes_passed < 8:  # still confirming
            return 45 - int(minutes_passed)
        elif minutes_passed < 20:  # preparing
            return 35 - int(minutes_passed - 8)
        else:  # out for delivery
            return max(1, 15 - int(minutes_passed - 20))
    
    def _generate_mock_order(self, service: str, restaurant: str, items: List[Dict[str, Any]], delivery_address: str) -> Dict[str, Any]:
        """
        Generate mock order details for demonstration purposes.
        
        Args:
            service: The food delivery service
            restaurant: The restaurant name
            items: List of food items with quantity and name
            delivery_address: The delivery address
            
        Returns:
            dict: Mock order details
        """
        # Generate a random order ID
        order_id = f"{service[0].upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate order details
        subtotal = 0.0
        
        # Assign random prices to items
        for item in items:
            # Generate item price based on name and quantity
            base_price = 0.0
            name_lower = item["name"].lower()
            
            if "pizza" in name_lower:
                base_price = random.uniform(12.0, 18.0)
            elif "burger" in name_lower:
                base_price = random.uniform(8.0, 14.0)
            elif "fries" in name_lower or "side" in name_lower:
                base_price = random.uniform(3.0, 6.0)
            elif "drink" in name_lower or "soda" in name_lower:
                base_price = random.uniform(2.0, 4.0)
            elif "combo" in name_lower or "meal" in name_lower:
                base_price = random.uniform(15.0, 25.0)
            elif "special" in name_lower:
                base_price = random.uniform(15.0, 30.0)
            else:
                base_price = random.uniform(10.0, 20.0)
            
            # Round to 99 cents format
            item_price = round(base_price) - 0.01
            
            # Add to item and calculate subtotal
            item["price"] = item_price
            subtotal += item_price * item["quantity"]
        
        # Calculate fees and taxes
        delivery_fee = round(random.uniform(2.0, 7.0) * 2) / 2 - 0.01
        tax_rate = 0.0825  # 8.25% tax rate
        tax = subtotal * tax_rate
        
        total = subtotal + delivery_fee + tax
        
        # Calculate delivery time
        now = datetime.now()
        delivery_minutes = random.randint(30, 60)
        delivery_time = now + timedelta(minutes=delivery_minutes)
        
        formatted_delivery_time = delivery_time.strftime("%-I:%M %p")  # e.g., "7:45 PM"
        
        return {
            "service": service,
            "order_id": order_id,
            "restaurant": restaurant,
            "items": items,
            "delivery_address": delivery_address,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "tax": tax,
            "total": total,
            "delivery_time": formatted_delivery_time,
            "estimated_minutes": delivery_minutes
        } 