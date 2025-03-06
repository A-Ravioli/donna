from typing import List, Dict, Any, Optional
import os
import tempfile
import base64

from langchain.chains import LLMChain, ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI, OpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool, Tool

# Try to import langchain-mcp-tools if available
try:
    from langchain_mcp_tools import convert_mcp_to_langchain_tools
    HAS_MCP_TOOLS = True
except ImportError:
    HAS_MCP_TOOLS = False

from src.config.settings import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    LLM_PROVIDER,
    COMPOSIO_API_KEY,
)


class LLMManager:
    """
    Manager for LLM integrations using LangChain.
    Supports multiple model providers and model types.
    """

    def __init__(self, provider=None, model_name=None):
        """
        Initialize the LLM manager.
        
        Args:
            provider (str, optional): The LLM provider to use. Defaults to the one in settings.
            model_name (str, optional): The model name to use. Defaults to provider-specific default.
        """
        self.provider = provider or LLM_PROVIDER
        self.model_name = model_name
        self.llm = self._initialize_llm()
        self.mcp_tools = []
        self.mcp_cleanup_fn = None
        
    def _initialize_llm(self) -> BaseChatModel:
        """
        Initialize the LLM based on the provider.
        
        Returns:
            BaseChatModel: The initialized LLM.
        """
        if self.provider == "openai":
            # Default to GPT-4o if not specified
            model = self.model_name or "gpt-4o"
            return ChatOpenAI(
                model=model,
                temperature=0.7,
                api_key=OPENAI_API_KEY
            )
        elif self.provider == "anthropic":
            # Default to Claude 3 Opus if not specified
            model = self.model_name or "claude-3-opus-20240229"
            return ChatAnthropic(
                model=model,
                temperature=0.7,
                api_key=ANTHROPIC_API_KEY
            )
        else:
            # Default to OpenAI if provider not recognized
            return ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=OPENAI_API_KEY
            )
    
    async def initialize_mcp_tools(self, mcp_configs=None):
        """
        Initialize MCP tools if langchain_mcp_tools is available.
        
        Args:
            mcp_configs (dict, optional): MCP server configurations.
                Example: {
                    'filesystem': {
                        'command': 'npx',
                        'args': ['-y', '@modelcontextprotocol/server-filesystem', '.']
                    },
                    'fetch': {
                        'command': 'uvx',
                        'args': ['mcp-server-fetch']
                    }
                }
                
        Returns:
            List[BaseTool]: List of LangChain-compatible tools from MCP servers.
        """
        if not HAS_MCP_TOOLS:
            print("Warning: langchain_mcp_tools not installed. MCP tools will not be available.")
            return []
            
        if not mcp_configs:
            # Default configurations if none provided
            mcp_configs = {
                'fetch': {
                    'command': 'uvx',
                    'args': ['mcp-server-fetch']
                }
            }
        
        try:
            self.mcp_tools, self.mcp_cleanup_fn = await convert_mcp_to_langchain_tools(mcp_configs)
            return self.mcp_tools
        except Exception as e:
            print(f"Error initializing MCP tools: {e}")
            return []
    
    async def cleanup_mcp_tools(self):
        """Clean up MCP tool resources when done."""
        if self.mcp_cleanup_fn:
            await self.mcp_cleanup_fn()
    
    def create_conversation_chain(self):
        """
        Create a conversation chain with memory.
        
        Returns:
            ConversationChain: A conversation chain with memory.
        """
        memory = ConversationBufferMemory()
        conversation = ConversationChain(
            llm=self.llm,
            memory=memory,
            verbose=True
        )
        return conversation
    
    def process_message(
        self, 
        message: str, 
        system_message: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        image_data: Optional[bytes] = None,
        tools: Optional[List[BaseTool]] = None,
    ) -> Dict[str, Any]:
        """
        Process a message using the LLM with support for images and tools.
        
        Args:
            message (str): The message to process.
            system_message (str, optional): An optional system message for context.
            chat_history (List[Dict[str, str]], optional): Previous chat history.
            image_data (bytes, optional): Binary image data to include with the message.
            tools (List[BaseTool], optional): Tools to make available to the LLM.
            
        Returns:
            Dict[str, Any]: The LLM's response with additional metadata.
        """
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        # Add chat history if provided
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add the current message, with image if provided
        if image_data and hasattr(self.llm, "with_image_url"):
            # Convert binary image data to base64 for model
            base64_image = base64.b64encode(image_data).decode("utf-8")
            image_url = f"data:image/jpeg;base64,{base64_image}"
            
            # Create multimodal content
            content = [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
            messages.append(HumanMessage(content=content))
        else:
            messages.append(HumanMessage(content=message))
            
        # Get the response
        if tools:
            # If tools are provided, use them with the model
            response = self.llm.invoke(messages, tools=tools)
        else:
            response = self.llm.invoke(messages)
        
        # Create response dictionary with content and metadata
        result = {
            "content": response.content,
            "metadata": {
                "model": self.model_name or self.provider,
                "timestamp": None,  # Can add timestamp if needed
            }
        }
        
        # Add tool calls if they exist
        if hasattr(response, "tool_calls") and response.tool_calls:
            result["tool_calls"] = response.tool_calls
            
        return result
    
    def create_custom_chain(self, prompt_template: str, output_key: str = "text"):
        """
        Create a custom LLM chain with a specific prompt template.
        
        Args:
            prompt_template (str): The prompt template to use.
            output_key (str, optional): The output key. Defaults to "text".
            
        Returns:
            LLMChain: The custom LLM chain.
        """
        prompt = PromptTemplate.from_template(prompt_template)
        chain = LLMChain(llm=self.llm, prompt=prompt, output_key=output_key)
        return chain 