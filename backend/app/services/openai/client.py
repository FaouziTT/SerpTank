"""
OpenAI API client for making requests to the OpenAI API.

This module handles the low-level HTTP communication with OpenAI's API.
"""
import logging
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for interacting with OpenAI API."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0
    ):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key
            base_url: Base URL for the API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for completion
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            **kwargs: Additional parameters for the API
            
        Returns:
            API response data
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenAI API request error: {e}")
            raise
    
    async def create_embedding(
        self,
        input_text: str,
        model: str = "text-embedding-ada-002"
    ) -> Dict[str, Any]:
        """
        Create an embedding using OpenAI API.
        
        Args:
            input_text: Text to create embedding for
            model: Embedding model to use
            
        Returns:
            API response data with embedding
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        payload = {
            "model": model,
            "input": input_text
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenAI API request error: {e}")
            raise
    
    async def moderate_content(
        self,
        input_text: str,
        model: str = "text-moderation-latest"
    ) -> Dict[str, Any]:
        """
        Check content for policy violations using OpenAI moderation API.
        
        Args:
            input_text: Text to moderate
            model: Moderation model to use
            
        Returns:
            API response data with moderation results
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        payload = {
            "model": model,
            "input": input_text
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/moderations",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"OpenAI API request error: {e}")
            raise