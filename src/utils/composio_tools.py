import asyncio
from typing import List, Dict, Any, Callable, Tuple, Optional

from langchain_core.tools import BaseTool, Tool
from src.integrations.composio_client import ComposioClient


def create_langchain_tool_from_composio(
    tool_name: str, 
    action_name: str, 
    description: str, 
    client: ComposioClient
) -> BaseTool:
    """
    Create a LangChain tool from a Composio tool and action.
    
    Args:
        tool_name (str): The name of the Composio tool.
        action_name (str): The name of the action to perform.
        description (str): A description of what the tool does.
        client (ComposioClient): The Composio client instance.
        
    Returns:
        BaseTool: A LangChain tool that wraps the Composio tool.
    """
    def _run_tool(**kwargs) -> Dict[str, Any]:
        """Run the Composio tool with the given parameters."""
        return client.execute_tool(
            tool_name=tool_name,
            action=action_name,
            params=kwargs
        )
        
    return Tool(
        name=f"{tool_name}_{action_name}",
        description=description,
        func=_run_tool
    )


async def get_composio_tools(api_key: Optional[str] = None) -> List[BaseTool]:
    """
    Get all available Composio tools and convert them to LangChain tools.
    
    Args:
        api_key (str, optional): Composio API key. If not provided, uses the one from settings.
        
    Returns:
        List[BaseTool]: A list of LangChain tools that wrap Composio tools.
    """
    client = ComposioClient(api_key)
    
    # Get available tools from Composio
    tools_data = client.list_available_tools()
    
    # Convert each tool action to a LangChain tool
    langchain_tools = []
    
    for tool in tools_data:
        tool_name = tool.get("name", "")
        if not tool_name:
            continue
            
        actions = tool.get("actions", [])
        for action in actions:
            action_name = action.get("name", "")
            description = action.get("description", "")
            if not action_name or not description:
                continue
                
            langchain_tool = create_langchain_tool_from_composio(
                tool_name=tool_name,
                action_name=action_name,
                description=description,
                client=client
            )
            
            langchain_tools.append(langchain_tool)
            
    return langchain_tools


def get_calendar_tools(client: Optional[ComposioClient] = None) -> List[BaseTool]:
    """
    Get calendar-related Composio tools as LangChain tools.
    
    Args:
        client (ComposioClient, optional): The Composio client. Creates a new one if not provided.
        
    Returns:
        List[BaseTool]: A list of LangChain tools for calendar operations.
    """
    client = client or ComposioClient()
    
    # Create calendar tools
    list_events_tool = create_langchain_tool_from_composio(
        tool_name="google_calendar",
        action_name="list_events",
        description="List events from a Google Calendar within a date range. Requires start_date and end_date in ISO format.",
        client=client
    )
    
    create_event_tool = create_langchain_tool_from_composio(
        tool_name="google_calendar",
        action_name="create_event",
        description="Create an event in Google Calendar. Requires summary, start_datetime, and end_datetime.",
        client=client
    )
    
    update_event_tool = create_langchain_tool_from_composio(
        tool_name="google_calendar",
        action_name="update_event",
        description="Update an existing event in Google Calendar. Requires event_id and any fields to update.",
        client=client
    )
    
    delete_event_tool = create_langchain_tool_from_composio(
        tool_name="google_calendar",
        action_name="delete_event",
        description="Delete an event from Google Calendar. Requires event_id.",
        client=client
    )
    
    return [
        list_events_tool,
        create_event_tool,
        update_event_tool,
        delete_event_tool
    ]


def get_notion_tools(client: Optional[ComposioClient] = None) -> List[BaseTool]:
    """
    Get Notion-related Composio tools as LangChain tools.
    
    Args:
        client (ComposioClient, optional): The Composio client. Creates a new one if not provided.
        
    Returns:
        List[BaseTool]: A list of LangChain tools for Notion operations.
    """
    client = client or ComposioClient()
    
    # Create Notion tools
    get_pages_tool = create_langchain_tool_from_composio(
        tool_name="notion",
        action_name="get_database_pages",
        description="Get pages from a Notion database. Requires database_id.",
        client=client
    )
    
    create_page_tool = create_langchain_tool_from_composio(
        tool_name="notion",
        action_name="create_page",
        description="Create a page in a Notion database. Requires database_id and properties.",
        client=client
    )
    
    update_page_tool = create_langchain_tool_from_composio(
        tool_name="notion",
        action_name="update_page",
        description="Update a page in Notion. Requires page_id and properties.",
        client=client
    )
    
    get_block_children_tool = create_langchain_tool_from_composio(
        tool_name="notion",
        action_name="get_block_children",
        description="Get the children blocks of a block in Notion. Requires block_id.",
        client=client
    )
    
    return [
        get_pages_tool,
        create_page_tool,
        update_page_tool,
        get_block_children_tool
    ] 