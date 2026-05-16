import asyncio
import json
import logging
from typing import Optional
from openai import OpenAI, AsyncOpenAI, OpenAIError
from app.core.config import settings
from app.core.exceptions import LLMUnavailableError

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.DIGITALOCEAN_BASE_URL,
            api_key=settings.DIGITALOCEAN_API_KEY,
            timeout=settings.DIGITALOCEAN_TIMEOUT_MS / 1000.0,
            max_retries=3
        )
        self.async_client = AsyncOpenAI(
            base_url=settings.DIGITALOCEAN_BASE_URL,
            api_key=settings.DIGITALOCEAN_API_KEY,
            timeout=settings.DIGITALOCEAN_TIMEOUT_MS / 1000.0,
            max_retries=3
        )
        self.model_id = settings.LLM_MODEL_ID
        self.embed_model_id = settings.EMBED_MODEL_ID

    def _prepare_kwargs(self, system_prompt: str, user_message: str, use_caching: bool, reasoning_effort: Optional[str], temperature: Optional[float] = None, tools: Optional[list] = None, tool_choice: Optional[dict] = None) -> dict:
        is_anthropic = "anthropic" in self.model_id.lower() or "claude" in self.model_id.lower()
        
        messages = []
        if is_anthropic and use_caching:
            messages.append({
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral", "ttl": "1h"}
                    }
                ]
            })
            messages.append({"role": "user", "content": user_message})
        else:
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

        kwargs = {
            "model": self.model_id,
            "messages": messages
        }
        
        if temperature is not None:
            kwargs["temperature"] = temperature
            
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        
        extra_body = {}
        
        if not is_anthropic and use_caching:
            extra_body["prompt_cache_retention"] = "24h"
            
        if reasoning_effort:
            if is_anthropic:
                extra_body["reasoning"] = {
                    "effort": reasoning_effort,
                    "max_tokens": 1024
                }
                kwargs["max_completion_tokens"] = 2048 # Recommended to supply max_completion_tokens when using reasoning
            else:
                extra_body["reasoning_effort"] = reasoning_effort
                kwargs["max_completion_tokens"] = 2048
                
        if extra_body:
            kwargs["extra_body"] = extra_body
            
        return kwargs

    def _invoke_llm_sync(self, system_prompt: str, user_message: str, temperature: float = 1.0, use_caching: bool = False, reasoning_effort: Optional[str] = None) -> str:
        try:
            kwargs = self._prepare_kwargs(system_prompt, user_message, use_caching, reasoning_effort, temperature=temperature)
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error(f"LLM invocation failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")

    async def invoke_llm(self, system_prompt: str, user_message: str, temperature: float = 1.0, use_caching: bool = False, reasoning_effort: Optional[str] = None) -> str:
        try:
            kwargs = self._prepare_kwargs(system_prompt, user_message, use_caching, reasoning_effort, temperature=temperature)
            response = await self.async_client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error(f"LLM async invocation failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")

    def _invoke_llm_structured_sync(self, system_prompt: str, user_message: str, tool_schema: dict, use_caching: bool = False, reasoning_effort: Optional[str] = None) -> dict:
        try:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "extract_structured_data",
                        "description": "Extract structured data based on the schema",
                        "parameters": tool_schema
                    }
                }
            ]
            
            kwargs = self._prepare_kwargs(
                system_prompt, 
                user_message, 
                use_caching, 
                reasoning_effort, 
                temperature=0.0,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "extract_structured_data"}}
            )
            
            response = self.client.chat.completions.create(**kwargs)
            
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                arguments = tool_calls[0].function.arguments
                return json.loads(arguments)
            
            return {}
        except OpenAIError as e:
            logger.error(f"LLM structured invocation failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from tool arguments: {e}")
            return {}

    async def invoke_llm_structured(self, system_prompt: str, user_message: str, tool_schema: dict, use_caching: bool = False, reasoning_effort: Optional[str] = None) -> dict:
        try:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "extract_structured_data",
                        "description": "Extract structured data based on the schema",
                        "parameters": tool_schema
                    }
                }
            ]
            
            kwargs = self._prepare_kwargs(
                system_prompt, 
                user_message, 
                use_caching, 
                reasoning_effort, 
                temperature=0.0,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "extract_structured_data"}}
            )
            
            response = await self.async_client.chat.completions.create(**kwargs)
            
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                arguments = tool_calls[0].function.arguments
                return json.loads(arguments)
            
            return {}
        except OpenAIError as e:
            logger.error(f"LLM structured async invocation failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from tool arguments: {e}")
            return {}

    def _embed_text_sync(self, text: str, input_type: str = "search_query") -> list[float]:
        try:
            response = self.client.embeddings.create(
                model=self.embed_model_id,
                input=text
            )
            return response.data[0].embedding
        except OpenAIError as e:
            logger.error(f"LLM embedding failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")

    async def embed_text(self, text: str, input_type: str = "search_query") -> list[float]:
        try:
            response = await self.async_client.embeddings.create(
                model=self.embed_model_id,
                input=text
            )
            return response.data[0].embedding
        except OpenAIError as e:
            logger.error(f"LLM async embedding failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")

    async def embed_texts(self, texts: list[str], input_type: str = "search_query") -> list[list[float]]:
        try:
            response = await self.async_client.embeddings.create(
                model=self.embed_model_id,
                input=texts
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [data.embedding for data in sorted_data]
        except OpenAIError as e:
            logger.error(f"LLM async batch embedding failed: {e}")
            raise LLMUnavailableError(f"LLM error: {e}")

llm_service = LLMService()
