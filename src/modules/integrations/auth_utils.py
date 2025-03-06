"""
Authentication utilities for platform integrations.
This module provides helper functions for handling OAuth and API key authentication
for various platform integrations.
"""

import os
import json
import secrets
import base64
from typing import Dict, Optional, Tuple
import sqlite3
import requests
from urllib.parse import urlencode

# Directory for storing secure tokens
TOKENS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tokens")
os.makedirs(TOKENS_DIR, exist_ok=True)

# OAuth state storage to prevent CSRF
OAUTH_STATES = {}

def generate_oauth_state(user_id: str, integration_name: str) -> str:
    """
    Generate a secure state parameter for OAuth flow.
    
    Args:
        user_id: The user's identifier
        integration_name: The name of the integration
        
    Returns:
        A secure random state string
    """
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = {
        "user_id": user_id,
        "integration_name": integration_name
    }
    return state

def verify_oauth_state(state: str) -> Optional[Dict[str, str]]:
    """
    Verify a state parameter from an OAuth callback.
    
    Args:
        state: The state parameter to verify
        
    Returns:
        The user info if valid, None otherwise
    """
    if state in OAUTH_STATES:
        user_info = OAUTH_STATES[state]
        del OAUTH_STATES[state]  # Use only once
        return user_info
    return None

def get_oauth_url(integration_name: str, user_id: str, scopes: list) -> str:
    """
    Get the OAuth URL for a specific integration.
    
    Args:
        integration_name: The name of the integration
        user_id: The user's identifier
        scopes: The OAuth scopes to request
        
    Returns:
        The OAuth authorization URL
    """
    state = generate_oauth_state(user_id, integration_name)
    
    # Google OAuth
    if integration_name == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = "https://your-donna-server.com/oauth/google/callback"
        scope = " ".join(scopes)
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    
    # Add more OAuth providers as needed
    elif integration_name == "slack":
        client_id = os.getenv("SLACK_CLIENT_ID")
        redirect_uri = "https://your-donna-server.com/oauth/slack/callback"
        scope = ",".join(scopes)
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state
        }
        
        return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"
    
    elif integration_name == "uber":
        client_id = os.getenv("UBER_CLIENT_ID") 
        redirect_uri = "https://your-donna-server.com/oauth/uber/callback"
        scope = " ".join(scopes)
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state
        }
        
        return f"https://login.uber.com/oauth/v2/authorize?{urlencode(params)}"
    
    return ""

def exchange_oauth_code(integration_name: str, code: str) -> Optional[Dict[str, str]]:
    """
    Exchange an OAuth authorization code for access and refresh tokens.
    
    Args:
        integration_name: The name of the integration
        code: The authorization code
        
    Returns:
        A dictionary containing the tokens if successful, None otherwise
    """
    redirect_uri = f"https://your-donna-server.com/oauth/{integration_name}/callback"
    
    # Google OAuth
    if integration_name == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        response = requests.post("https://oauth2.googleapis.com/token", data=data)
        if response.status_code == 200:
            return response.json()
    
    # Add more OAuth providers as needed
    elif integration_name == "slack":
        client_id = os.getenv("SLACK_CLIENT_ID")
        client_secret = os.getenv("SLACK_CLIENT_SECRET")
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        
        response = requests.post("https://slack.com/api/oauth.v2.access", data=data)
        if response.status_code == 200:
            return response.json()
    
    return None

def refresh_oauth_token(integration_name: str, refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Refresh an OAuth access token using a refresh token.
    
    Args:
        integration_name: The name of the integration
        refresh_token: The refresh token
        
    Returns:
        A dictionary containing the new tokens if successful, None otherwise
    """
    # Google OAuth
    if integration_name == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post("https://oauth2.googleapis.com/token", data=data)
        if response.status_code == 200:
            return response.json()
    
    # Add more OAuth providers as needed
    
    return None

def get_api_key(integration_name: str) -> Optional[str]:
    """
    Get the API key for a specific integration.
    
    Args:
        integration_name: The name of the integration
        
    Returns:
        The API key if available, None otherwise
    """
    env_var_name = f"{integration_name.upper()}_API_KEY"
    return os.getenv(env_var_name)

def store_oauth_tokens(user_id: str, integration_name: str, tokens: Dict[str, str]) -> bool:
    """
    Store OAuth tokens securely.
    
    Args:
        user_id: The user's identifier
        integration_name: The name of the integration
        tokens: The tokens to store
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a token file specific to this user and integration
        token_file = os.path.join(TOKENS_DIR, f"{user_id}_{integration_name}_tokens.json")
        
        # Store the tokens
        with open(token_file, "w") as f:
            json.dump(tokens, f)
        
        return True
    except Exception as e:
        print(f"Error storing OAuth tokens: {e}")
        return False

def get_oauth_tokens(user_id: str, integration_name: str) -> Optional[Dict[str, str]]:
    """
    Get stored OAuth tokens.
    
    Args:
        user_id: The user's identifier
        integration_name: The name of the integration
        
    Returns:
        The stored tokens if available, None otherwise
    """
    try:
        # Get the token file specific to this user and integration
        token_file = os.path.join(TOKENS_DIR, f"{user_id}_{integration_name}_tokens.json")
        
        # Check if the file exists
        if not os.path.exists(token_file):
            return None
        
        # Read the tokens
        with open(token_file, "r") as f:
            tokens = json.load(f)
        
        return tokens
    except Exception as e:
        print(f"Error getting OAuth tokens: {e}")
        return None 