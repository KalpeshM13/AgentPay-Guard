"""Gemini LLM provider — Google's Gemini via the generative-language SDK.

Uses ``google-genai``.  Install with ``pip install google-genai`` (optional).
If the SDK or API key is missing, the provider is silently unavailable.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini (default: gemini-2.5-flash)."""

    provider_name = "gemini"

    def __init__(self) -> None:
        super().__init__(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_DEFAULT_MODEL

        if self.is_available:
            try:
                from google import genai

                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "google-genai SDK not installed; Gemini provider is "
                    "unavailable. Install with: pip install google-genai"
                )
                self._available = False
            except Exception:
                logger.exception("Failed to initialise Gemini client")
                self._available = False

    async def _call(self, prompt: str, max_tokens: int) -> str:
        """Send a generate-content request to Gemini."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config={
                "system_instruction": (
                    "You are an assistant that explains financial policy "
                    "decisions in plain, non-technical English.  Be "
                    "concise (1-2 sentences unless asked for more).  "
                    "Never suggest bypassing security controls."
                ),
                "max_output_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        return response.text.strip()
