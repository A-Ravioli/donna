import json
import requests
from typing import Dict, Any, List, Optional

from src.config.settings import COMPOSIO_API_KEY


class ComposioClient:
    """Client for integrating with Composio MCP services."""
    
    def __init__(self, api_key=None):
        """
        Initialize the Composio client.
        
        Args:
            api_key (str, optional): Composio API key. Defaults to value from settings.
        """
        self.api_key = api_key or COMPOSIO_API_KEY
        self.base_url = "https://api.composio.dev"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available tools from Composio.
        
        Returns:
            List[Dict[str, Any]]: List of available tools.
        """
        try:
            response = requests.get(
                f"{self.base_url}/v1/tools",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json().get("tools", [])
        except Exception as e:
            print(f"Error listing Composio tools: {e}")
            return []
            
    def execute_tool(self, tool_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific tool action with parameters.
        
        Args:
            tool_name (str): The name of the tool to use.
            action (str): The action to perform with the tool.
            params (Dict[str, Any]): Parameters for the action.
            
        Returns:
            Dict[str, Any]: Response from the tool execution.
        """
        try:
            payload = {
                "tool": tool_name,
                "action": action,
                "parameters": params
            }
            
            response = requests.post(
                f"{self.base_url}/v1/execute",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error executing Composio tool {tool_name}.{action}: {e}")
            return {"error": str(e)}
            
    def connect_calendar(self, calendar_id: str) -> Dict[str, Any]:
        """
        Connect to a Google Calendar.
        
        Args:
            calendar_id (str): The ID of the Google Calendar to connect to.
            
        Returns:
            Dict[str, Any]: Response from the calendar connection.
        """
        return self.execute_tool(
            tool_name="google_calendar",
            action="connect",
            params={"calendar_id": calendar_id}
        )
        
    def list_calendar_events(self, 
                             start_date: str, 
                             end_date: str, 
                             calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List events from a Google Calendar.
        
        Args:
            start_date (str): Start date in ISO format.
            end_date (str): End date in ISO format.
            calendar_id (str, optional): Calendar ID. If not provided, uses primary calendar.
            
        Returns:
            Dict[str, Any]: Calendar events.
        """
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        if calendar_id:
            params["calendar_id"] = calendar_id
            
        return self.execute_tool(
            tool_name="google_calendar",
            action="list_events",
            params=params
        )
        
    def create_calendar_event(self, 
                             summary: str,
                             start_datetime: str,
                             end_datetime: str,
                             description: Optional[str] = None,
                             location: Optional[str] = None,
                             calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an event in a Google Calendar.
        
        Args:
            summary (str): Event title.
            start_datetime (str): Start time in ISO format.
            end_datetime (str): End time in ISO format.
            description (str, optional): Event description.
            location (str, optional): Event location.
            calendar_id (str, optional): Calendar ID. If not provided, uses primary calendar.
            
        Returns:
            Dict[str, Any]: Created event details.
        """
        params = {
            "summary": summary,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime
        }
        
        if description:
            params["description"] = description
        
        if location:
            params["location"] = location
            
        if calendar_id:
            params["calendar_id"] = calendar_id
            
        return self.execute_tool(
            tool_name="google_calendar",
            action="create_event",
            params=params
        )
        
    def retrieve_notion_pages(self, database_id: str) -> Dict[str, Any]:
        """
        Retrieve pages from a Notion database.
        
        Args:
            database_id (str): The ID of the Notion database.
            
        Returns:
            Dict[str, Any]: Pages from the database.
        """
        return self.execute_tool(
            tool_name="notion",
            action="get_database_pages",
            params={"database_id": database_id}
        )
        
    def create_notion_page(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a page in a Notion database.
        
        Args:
            database_id (str): The ID of the Notion database.
            properties (Dict[str, Any]): Properties for the new page.
            
        Returns:
            Dict[str, Any]: Created page details.
        """
        return self.execute_tool(
            tool_name="notion",
            action="create_page",
            params={
                "database_id": database_id,
                "properties": properties
            }
        )
        
    def generate_image(self, prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        """
        Generate an image using DALL-E through Composio.
        
        Args:
            prompt (str): Description of the image to generate.
            size (str, optional): Image size. Defaults to "1024x1024".
            
        Returns:
            Dict[str, Any]: Generated image information.
        """
        return self.execute_tool(
            tool_name="dall_e",
            action="generate_image",
            params={
                "prompt": prompt,
                "size": size
            }
        )
        
    def search_web(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Search the web using Composio's search tool.
        
        Args:
            query (str): The search query.
            num_results (int, optional): Number of results to return. Defaults to 5.
            
        Returns:
            Dict[str, Any]: Search results.
        """
        return self.execute_tool(
            tool_name="web_search",
            action="search",
            params={
                "query": query,
                "num_results": num_results
            }
        ) 