"""LLM Client module for OpenAI API interactions.

This module provides a wrapper class for OpenAI client configuration
and chat completion functionality.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClient:
    """Client wrapper for OpenAI API interactions."""

    def __init__(self):
        """Initialize the LLM client with configuration from environment variables."""
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.base_url:
            self.model = os.getenv("MODEL")
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        else:
            self.model = os.getenv("OPENAI_MODEL")
            self.client = OpenAI(api_key=self.api_key)

    def get_client(self):
        """Return the OpenAI client instance."""
        return self.client

    def get_model(self):
        """Return the configured model name."""
        return self.model

    def chat_completion(self, messages, response_format=None, **kwargs):
        """Create a chat completion request.
        
        Args:
            messages: List of message objects for the conversation
            response_format: Optional response format specification
            **kwargs: Additional parameters for the API call
            
        Returns:
            OpenAI chat completion response
        """
        params = {
            "model": self.model,
            "messages": messages
        }
        if response_format:
            params["response_format"] = response_format
        params.update(kwargs)
        return self.client.chat.completions.create(**params)
