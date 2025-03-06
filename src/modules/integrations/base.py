import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import sqlite3

# Create a secure directory for storing credentials
CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials')
os.makedirs(CREDENTIALS_DIR, exist_ok=True)

class BaseIntegration(ABC):
    """Base class for all platform integrations."""
    
    def __init__(self):
        self.name = self.get_name()
        self.initialized = False
        self.conn = sqlite3.connect("integrations.db")
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables for this integration."""
        c = self.conn.cursor()
        
        # Create credentials table
        c.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                integration_name TEXT,
                credentials TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, integration_name)
            )
        ''')
        
        # Create integration-specific table
        table_query = self.get_table_schema()
        if table_query:
            c.execute(table_query)
            
        self.conn.commit()
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this integration."""
        pass
    
    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return a list of commands this integration can handle."""
        pass
    
    def get_table_schema(self) -> Optional[str]:
        """Return SQL to create an integration-specific table, or None if not needed."""
        return None
    
    @abstractmethod
    def can_handle(self, message: str) -> bool:
        """
        Check if this integration can handle the given message.
        
        Args:
            message: The message to check
            
        Returns:
            bool: True if this integration can handle the message
        """
        pass
    
    @abstractmethod
    def process(self, user_id: str, message: str, **kwargs) -> str:
        """
        Process a command for this integration.
        
        Args:
            user_id: The ID of the user
            message: The message to process
            kwargs: Additional arguments
            
        Returns:
            str: The response
        """
        pass
    
    def store_credentials(self, user_id: str, credentials: Dict[str, Any]) -> bool:
        """
        Store user credentials for this integration.
        
        Args:
            user_id: The ID of the user
            credentials: The credentials to store
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            creds_json = json.dumps(credentials)
            
            c.execute('''
                INSERT OR REPLACE INTO credentials
                (user_id, integration_name, credentials)
                VALUES (?, ?, ?)
            ''', (user_id, self.name, creds_json))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error storing credentials: {e}")
            return False
    
    def get_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user credentials for this integration.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            dict: The credentials, or None if not found
        """
        try:
            c = self.conn.cursor()
            c.execute('''
                SELECT credentials
                FROM credentials
                WHERE user_id = ? AND integration_name = ?
            ''', (user_id, self.name))
            
            result = c.fetchone()
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None
    
    def delete_credentials(self, user_id: str) -> bool:
        """
        Delete user credentials for this integration.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            bool: True if successful
        """
        try:
            c = self.conn.cursor()
            c.execute('''
                DELETE FROM credentials
                WHERE user_id = ? AND integration_name = ?
            ''', (user_id, self.name))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting credentials: {e}")
            return False
    
    def is_authenticated(self, user_id: str) -> bool:
        """
        Check if a user is authenticated for this integration.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            bool: True if authenticated
        """
        return self.get_credentials(user_id) is not None
    
    def get_authentication_instructions(self) -> str:
        """
        Get instructions for authenticating with this integration.
        
        Returns:
            str: Authentication instructions
        """
        return f"To use {self.name}, you need to authenticate first. Please provide your credentials."
    
    def close(self):
        """Close database connections and clean up."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


class IntegrationRegistry:
    """Registry for all available integrations."""
    
    def __init__(self):
        self.integrations = {}
    
    def register(self, integration: BaseIntegration):
        """
        Register an integration.
        
        Args:
            integration: The integration to register
        """
        self.integrations[integration.get_name()] = integration
    
    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """
        Get an integration by name.
        
        Args:
            name: The name of the integration
            
        Returns:
            BaseIntegration: The integration, or None if not found
        """
        return self.integrations.get(name)
    
    def get_all_integrations(self) -> List[BaseIntegration]:
        """
        Get all registered integrations.
        
        Returns:
            list: All integrations
        """
        return list(self.integrations.values())
    
    def find_integration_for_message(self, message: str) -> Optional[BaseIntegration]:
        """
        Find an integration that can handle a message.
        
        Args:
            message: The message
            
        Returns:
            BaseIntegration: The integration, or None if not found
        """
        for integration in self.integrations.values():
            if integration.can_handle(message):
                return integration
        return None
    
    def process_message(self, user_id: str, message: str) -> Optional[str]:
        """
        Process a message with the appropriate integration.
        
        Args:
            user_id: The ID of the user
            message: The message
            
        Returns:
            str: The response, or None if no integration can handle the message
        """
        integration = self.find_integration_for_message(message)
        if integration:
            return integration.process(user_id, message)
        return None 