"""
LLM Provider Implementations

Supports multiple LLM backends:
- OpenAI (GPT-4, recommended)
- Ollama (local development)
- AWS Bedrock (production)
- Hugging Face (alternative)
"""

import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for GPT models."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using OpenAI API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
        )

        if stream:
            return self._stream_response(response)
        else:
            return response.choices[0].message.content or ""

    async def _stream_response(self, response) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            # Simple models list call to verify API key works
            await self.client.models.list()
            return True
        except Exception:
            return False


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using Ollama."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.model,
                "messages": messages,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
                "stream": stream,
            }

            if stream:
                return self._stream_response(client, payload)
            else:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

    async def _stream_response(
        self, client: httpx.AsyncClient, payload: dict
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        async with client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class BedrockProvider(BaseLLMProvider):
    """AWS Bedrock provider for production LLM inference."""

    def __init__(self):
        self.region = settings.aws_region
        self.model_id = settings.bedrock_model_id
        self._client = None

    def _get_client(self):
        """Lazy initialization of Bedrock client."""
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )
        return self._client

    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using AWS Bedrock."""
        import asyncio

        client = self._get_client()

        # Format messages for Bedrock Llama format
        formatted_prompt = self._format_messages_for_llama(messages)

        body = json.dumps({
            "prompt": formatted_prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
        })

        # Run synchronous boto3 call in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
        )

        response_body = json.loads(response["body"].read())
        return response_body.get("generation", "")

    def _format_messages_for_llama(self, messages: list[dict]) -> str:
        """Format messages for Llama chat format."""
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "user":
                formatted += f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>"
            elif role == "assistant":
                formatted += f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>"
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n"
        return formatted

    async def health_check(self) -> bool:
        """Check if Bedrock is accessible."""
        try:
            client = self._get_client()
            # Simple check - list foundation models
            client.list_foundation_models()
            return True
        except Exception:
            return False


class HuggingFaceProvider(BaseLLMProvider):
    """Hugging Face Inference API provider."""

    def __init__(self):
        self.model_id = settings.hf_model_id
        self.api_token = settings.hf_api_token
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"

    async def generate(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """Generate response using Hugging Face Inference API."""
        # Convert messages to a single prompt
        prompt = self._format_messages(messages)

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "return_full_text": False,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "")
            return ""

    def _format_messages(self, messages: list[dict]) -> str:
        """Format messages for Hugging Face models."""
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"System: {content}\n\n"
            elif role == "user":
                formatted += f"User: {content}\n\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n\n"
        formatted += "Assistant: "
        return formatted

    async def health_check(self) -> bool:
        """Check if Hugging Face API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://huggingface.co/api/models/{self.model_id}"
                )
                return response.status_code == 200
        except Exception:
            return False


def get_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider."""
    providers = {
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "bedrock": BedrockProvider,
        "huggingface": HuggingFaceProvider,
    }

    provider_class = providers.get(settings.llm_provider)
    if provider_class is None:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    return provider_class()
