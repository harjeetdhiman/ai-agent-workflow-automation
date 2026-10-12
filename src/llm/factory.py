import os
from src.llm.base import BaseLLMProvider
from src.llm.mock_provider import MockLLMProvider
from src.llm.openai_provider import OpenAIProvider
from src.config import LLM_PROVIDER, OPENAI_API_KEY


def get_llm_provider(force_provider: str = None) -> BaseLLMProvider:
    """
    Factory function returning the configured LLM provider.
    - If force_provider is specified ('openai' or 'mock'), returns that.
    - If LLM_PROVIDER is 'mock', returns MockLLMProvider.
    - If LLM_PROVIDER is 'openai' or 'auto', returns OpenAIProvider (which automatically
      falls back to MockLLMProvider if OPENAI_API_KEY is unset or invalid).
    """
    provider_name = (force_provider or LLM_PROVIDER).lower()

    if provider_name == "mock":
        return MockLLMProvider()

    if provider_name == "openai":
        return OpenAIProvider()

    # 'auto' mode
    if OPENAI_API_KEY and len(OPENAI_API_KEY.strip()) > 10:
        return OpenAIProvider()

    return MockLLMProvider()
