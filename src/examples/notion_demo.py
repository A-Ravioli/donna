#!/usr/bin/env python3
"""
Demo script to showcase the Notion integration through Composio.
This script demonstrates:
- Retrieving Notion database pages
- Creating new pages in a database
- Updating existing pages
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
import json

# Add the parent directory to the path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.integrations.composio_client import ComposioClient
from src.utils.composio_tools import get_notion_tools
from src.models.llm_manager import LLMManager


async def demo_notion_integration():
    """Demonstrate Notion integration with Composio."""
    print("=== Demonstrating Notion Integration with Composio ===")
    
    client = ComposioClient()
    
    # Replace with your actual database ID
    # You can find this in the URL of your Notion database:
    # https://www.notion.so/{workspace_name}/{database_id}?v={view_id}
    database_id = "your-notion-database-id"
    
    print("\n🔹 Checking if a valid database ID is provided")
    if database_id == "your-notion-database-id":
        print("Please replace 'your-notion-database-id' with your actual Notion database ID.")
        print("This demo will simulate the actions instead.")
        database_id = "simulated-database-id"
        
    # List pages in the database
    print(f"\n🔹 Listing pages from database: {database_id}")
    try:
        results = client.retrieve_notion_pages(database_id)
        
        if "error" in results:
            print(f"Error: {results['error']}")
            print("Continuing with simulated data...")
            
            # Simulated response
            simulated_pages = [
                {"id": "page-1", "properties": {"Name": {"title": [{"plain_text": "Task 1"}]}, "Status": {"select": {"name": "In Progress"}}}},
                {"id": "page-2", "properties": {"Name": {"title": [{"plain_text": "Task 2"}]}, "Status": {"select": {"name": "Not Started"}}}},
                {"id": "page-3", "properties": {"Name": {"title": [{"plain_text": "Task 3"}]}, "Status": {"select": {"name": "Completed"}}}},
            ]
            
            print("\nSimulated Pages:")
            for page in simulated_pages:
                title = page["properties"]["Name"]["title"][0]["plain_text"]
                status = page["properties"]["Status"]["select"]["name"]
                print(f"- {title} (Status: {status})")
        else:
            print("\nPages in database:")
            for page in results.get("pages", []):
                properties = page.get("properties", {})
                # Try to extract the title (format may vary)
                title = "Unknown"
                for prop in properties.values():
                    if "title" in prop:
                        try:
                            title = prop["title"][0]["plain_text"]
                            break
                        except (KeyError, IndexError):
                            pass
                print(f"- {title}")
    except Exception as e:
        print(f"Error retrieving Notion pages: {e}")
        print("Note: This demo requires a configured Composio account with Notion access")
    
    # Create a new page
    print("\n🔹 Creating a new page in the database")
    try:
        # Properties will depend on your database structure
        properties = {
            "Name": {"title": [{"text": {"content": "Task from Assistant"}}]},
            "Status": {"select": {"name": "Not Started"}},
            "Priority": {"select": {"name": "High"}},
            "Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
        }
        
        result = client.create_notion_page(database_id, properties)
        
        if "error" in result:
            print(f"Error: {result['error']}")
            print("Simulating successful page creation...")
            print("Page created successfully (simulated)!")
        else:
            print("Page created successfully!")
            print(f"Page ID: {result.get('id', 'unknown')}")
    except Exception as e:
        print(f"Error creating Notion page: {e}")
        print("Note: This demo requires a configured Composio account with Notion access")


async def demo_notion_with_langchain():
    """Demonstrate using LangChain with Notion tools."""
    print("\n=== Demonstrating LangChain with Notion Tools ===")
    
    llm_manager = LLMManager(provider="openai", model_name="gpt-4o")
    
    # Get Notion tools
    client = ComposioClient()
    notion_tools = get_notion_tools(client)
    
    # Process a message with tools
    print("\n🔹 Processing message with Notion tools")
    response = llm_manager.process_message(
        message="Create a new task in my Notion database titled 'Follow up with clients' with high priority.",
        system_message="You are a helpful assistant that can manage tasks in Notion.",
        tools=notion_tools
    )
    
    print(f"Response: {response['content']}")


async def run_demos():
    """Run all demos."""
    print("🚀 Notion Integration Demo Script 🚀")
    print("This script demonstrates Notion integration through Composio.\n")
    
    await demo_notion_integration()
    await demo_notion_with_langchain()
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(run_demos()) 