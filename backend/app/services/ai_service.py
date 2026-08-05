"""Unified AI service — single entry point for all AI-powered features.

Automatically picks the first available provider (Groq → Gemini → fallback).
If no API keys are configured, all methods return deterministic fallback
explanations — the backend continues working normally.

**AI is never used inside payment approval.**  These functions are only
called by the explain/summarise endpoints and are purely advisory.
"""

from __future__ import annotations

import logging

from app.services.ai.base import AIProvider
from app.services.ai.gemini_service import GeminiProvider
from app.services.ai.groq_service import GroqProvider

logger = logging.getLogger(__name__)




class _NoOpProvider:
    """Provides pure fallback explanations when no API key is configured.

    Delegates to the module-level fallback functions in ``ai.base``.
    """

    provider_name = "fallback"
    is_available = False

    async def explain_blocked_payment(self, reason, agent_name, merchant_name, amount):
        from app.services.ai.base import _fallback_explain_blocked
        return _fallback_explain_blocked(reason, agent_name, merchant_name, amount)

    async def explain_policy(self, agent_name, policy):
        from app.services.ai.base import _fallback_explain_policy
        return _fallback_explain_policy(agent_name, policy)

    async def summarize_audit(self, events):
        from app.services.ai.base import _fallback_summarize_audit
        return _fallback_summarize_audit(events)



_provider: AIProvider | _NoOpProvider | None = None


def _get_provider() -> AIProvider | _NoOpProvider:
    """Return the first available AI provider, or a no-op fallback."""
    global _provider

    if _provider is not None:
        return _provider

    groq = GroqProvider()
    if groq.is_available:
        logger.info("AI: using Groq provider (model=%s)", groq._model)
        _provider = groq
        return _provider

    gemini = GeminiProvider()
    if gemini.is_available:
        logger.info("AI: using Gemini provider (model=%s)", gemini._model)
        _provider = gemini
        return _provider

    logger.info("AI: no provider configured — using deterministic fallbacks")
    _provider = _NoOpProvider()
    return _provider




async def explain_blocked_payment(
    reason: str, agent_name: str, merchant_name: str, amount: float,
) -> str:
    """Return a human-readable explanation of why a payment was blocked."""
    return await _get_provider().explain_blocked_payment(
        reason, agent_name, merchant_name, amount,
    )


async def explain_policy(agent_name: str, policy: dict) -> str:
    """Return a human-readable summary of an agent's spending policy."""
    return await _get_provider().explain_policy(agent_name, policy)


async def summarize_audit(events: list[dict]) -> str:
    """Return a human-readable summary of recent audit log activity."""
    return await _get_provider().summarize_audit(events)
