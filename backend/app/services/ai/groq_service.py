"""Groq LLM provider — fast inference via the Groq Cloud API.

Uses the ``groq`` Python SDK.  Install with ``pip install groq`` (optional).
If the SDK or API key is missing, the provider is silently unavailable.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq-hosted Llama models (default: llama-3.1-8b-instant)."""

    provider_name = "groq"

    def __init__(self) -> None:
        super().__init__(api_key=settings.GROQ_API_KEY)
        self._model = settings.GROQ_DEFAULT_MODEL

        if self.is_available:
            try:
                from groq import AsyncGroq

                self._client = AsyncGroq(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "groq SDK not installed; Groq provider is unavailable. "
                    "Install with: pip install groq"
                )
                self._available = False
            except Exception:
                logger.exception("Failed to initialise Groq client")
                self._available = False

    async def _call(self, prompt: str, max_tokens: int) -> str:
        """Send a chat-completion request to Groq."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that explains financial policy "
                        "decisions in plain, non-technical English.  Be "
                        "concise (1-2 sentences unless asked for more).  "
                        "Never suggest bypassing security controls."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
