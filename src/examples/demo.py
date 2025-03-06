#!/usr/bin/env python3
"""
Demo script to showcase the usage of the iMessage Assistant with LangChain and Composio.
This script demonstrates:
- Initializing the LLM manager with different models
- Using Composio for calendar integration
- Processing messages with the assistant
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.models.llm_manager import LLMManager
from src.integrations.composio_client import ComposioClient
from src.utils.composio_tools import get_calendar_tools, get_notion_tools
from src.services.messaging import MessagingService
from src.config.settings import OPENAI_API_KEY, ANTHROPIC_API_KEY


async def demo_langchain_models():
    """Demonstrate using different LLM models with LangChain."""
    print("=== Demonstrating LangChain Model Integration ===")
    
    # Initialize with OpenAI
    print("\n🔹 Using OpenAI GPT-4o")
    llm_manager = LLMManager(provider="openai", model_name="gpt-4o")
    response = llm_manager.process_message(
        message="What are 3 ways to improve productivity?",
        system_message="You are a helpful productivity assistant."
    )
    print(f"Response: {response['content']}")
    
    # Initialize with Anthropic
    if ANTHROPIC_API_KEY:
        print("\n🔹 Using Anthropic Claude")
        llm_manager = LLMManager(provider="anthropic", model_name="claude-3-haiku-20240307")
        response = llm_manager.process_message(
            message="What are 3 ways to improve productivity?",
            system_message="You are a helpful productivity assistant."
        )
        print(f"Response: {response['content']}")
    else:
        print("\n🔹 Skipping Anthropic Claude (no API key)")


async def demo_composio_calendar():
    """Demonstrate Composio calendar integration."""
    print("\n=== Demonstrating Composio Calendar Integration ===")
    
    client = ComposioClient()
    
    # List calendar events (this is a simulated example)
    print("\n🔹 Listing calendar events for the next week")
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    try:
        events = client.list_calendar_events(
            start_date=today,
            end_date=next_week
        )
        
        if "error" in events:
            print(f"Error: {events['error']}")
        else:
            print("Calendar events:")
            for event in events.get("events", []):
                print(f"- {event.get('summary')} ({event.get('start_date')})")
    except Exception as e:
        print(f"Error accessing calendar: {e}")
        print("Note: This demo requires a configured Composio account with Google Calendar access")
    
    # Create a calendar event (simulated)
    print("\n🔹 Creating a sample calendar event")
    event_start = (datetime.now() + timedelta(hours=1)).isoformat()
    event_end = (datetime.now() + timedelta(hours=2)).isoformat()
    
    try:
        result = client.create_calendar_event(
            summary="Demo Meeting from Assistant",
            start_datetime=event_start,
            end_datetime=event_end,
            description="This is a demo event created by the assistant."
        )
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Event created: {result.get('summary', 'Demo Meeting')}")
    except Exception as e:
        print(f"Error creating event: {e}")
        print("Note: This demo requires a configured Composio account with Google Calendar access")


async def demo_langchain_with_tools():
    """Demonstrate using LangChain with Composio tools."""
    print("\n=== Demonstrating LangChain with Composio Tools ===")
    
    llm_manager = LLMManager(provider="openai", model_name="gpt-4o")
    
    # Get calendar tools
    client = ComposioClient()
    calendar_tools = get_calendar_tools(client)
    
    # Initialize MCP tools if available
    try:
        mcp_tools = await llm_manager.initialize_mcp_tools()
        print(f"\n🔹 Initialized {len(mcp_tools)} MCP tools")
    except Exception as e:
        print(f"\n🔹 Error initializing MCP tools: {e}")
        mcp_tools = []
    
    # Combine tools
    tools = calendar_tools + mcp_tools
    
    # Process a message with tools
    print("\n🔹 Processing message with tools")
    response = llm_manager.process_message(
        message="Schedule a meeting with my team tomorrow at 3pm titled 'Project Planning'",
        system_message="You are a helpful assistant that can manage calendars.",
        tools=tools
    )
    
    print(f"Response: {response['content']}")
    
    # Cleanup MCP tools
    if mcp_tools:
        await llm_manager.cleanup_mcp_tools()


async def demo_messaging_service():
    """Demonstrate the messaging service."""
    print("\n=== Demonstrating Messaging Service ===")
    
    messaging = MessagingService()
    
    # This is a simulation - it will only work if you have a BlueBubbles server configured
    test_chat_guid = "example-chat-guid"
    
    print(f"\n🔹 Sending a test message (note: requires a configured BlueBubbles server)")
    result = messaging.send_text(test_chat_guid, "This is a test message from the demo script.")
    
    if result:
        print("Message sent successfully!")
    else:
        print("Message could not be sent. Check your BlueBubbles configuration.")


async def run_demos():
    """Run all demos."""
    print("🚀 iMessage Assistant Demo Script 🚀")
    print("This script demonstrates various capabilities of the assistant.\n")
    
    await demo_langchain_models()
    await demo_composio_calendar()
    await demo_langchain_with_tools()
    await demo_messaging_service()
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(run_demos()) 