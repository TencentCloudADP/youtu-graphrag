import os
import time
import json
import requests
import re

from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv

from utils.logger import logger

try:
    from config import get_config
except ImportError:
    get_config = None

load_dotenv()

class LLMCompletionCall:
    def __init__(self):
        llm_config = self._load_llm_config()
        self.llm_model = os.getenv("LLM_MODEL", llm_config.model)
        self.llm_base_url = os.getenv("LLM_BASE_URL", llm_config.base_url)
        self.llm_api_key = os.getenv("LLM_API_KEY", llm_config.api_key)
        if not self.llm_api_key:
            raise ValueError("LLM API key not provided")
        self.openai_provider = os.getenv("OPENAI_PROVIDER", llm_config.provider).lower()
        self.temperature = self._get_float_env("LLM_TEMPERATURE", llm_config.temperature)
        self.max_tokens = self._get_int_env("LLM_MAX_TOKENS", llm_config.max_tokens)
        if self.openai_provider == "azure":
            self.api_version = os.getenv("API_VERSION", llm_config.api_version)
            self.client = AzureOpenAI(
                    azure_endpoint=self.llm_base_url,
                    api_key=self.llm_api_key,
                    api_version=self.api_version,
                )
        else:
            self.client = OpenAI(base_url=self.llm_base_url, api_key = self.llm_api_key)

    def _load_llm_config(self):
        if get_config is None:
            return _DefaultLLMConfig()
        try:
            config = get_config()
            return getattr(config, "llm", _DefaultLLMConfig())
        except Exception as e:
            logger.warning(f"Failed to load LLM config, using defaults: {e}")
            return _DefaultLLMConfig()

    def _get_float_env(self, env_name: str, default: float) -> float:
        raw_value = os.getenv(env_name)
        if raw_value is None or raw_value == "":
            return default
        try:
            return float(raw_value)
        except ValueError:
            logger.warning(f"Invalid {env_name}={raw_value!r}; using {default}")
            return default

    def _get_int_env(self, env_name: str, default):
        raw_value = os.getenv(env_name)
        if raw_value is None or raw_value == "":
            return default
        try:
            return int(raw_value)
        except ValueError:
            logger.warning(f"Invalid {env_name}={raw_value!r}; using {default}")
            return default

    def call_api(self, content: str) -> str:
        """
        Call API to generate text with retry mechanism.
        
        Args:
            content: Prompt content
            
        Returns:
            Generated text response
        """
            
        try:
            params = {
                "model": self.llm_model,
                "messages": [{"role": "user", "content": content}],
                "temperature": self.temperature,
            }
            if self.max_tokens is not None:
                params["max_tokens"] = self.max_tokens

            completion = self.client.chat.completions.create(**params)
            raw = completion.choices[0].message.content or ""
            clean_completion = self._clean_llm_content(raw)
            return clean_completion
            
        except Exception as e:
            logger.error(f"LLM api calling failed. Error: {e}")
            raise e 

    def _clean_llm_content(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
        fence_re = re.compile(r"^\s*```(?:\s*\w+)?\s*\n(?P<body>[\s\S]*?)\n\s*```\s*$", re.MULTILINE)
        m = fence_re.match(t)
        if m:
            t = m.group("body").strip()
        else:
            if t.startswith("```") and t.endswith("```") and len(t) >= 6:
                t = t[3:-3].strip()

        if t.lower().startswith("json\n"):
            t = t.split("\n", 1)[1].strip()

        return t


class _DefaultLLMConfig:
    model = "deepseek-chat"
    base_url = "https://api.deepseek.com"
    api_key = ""
    provider = "openai"
    api_version = "2025-01-01-preview"
    temperature = 0.3
    max_tokens = None
