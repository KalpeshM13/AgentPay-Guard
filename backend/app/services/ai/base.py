"""Base class for AI providers.

Every provider:
- Is instantiated with an API key; missing key → ``is_available == False``.
- Implements ``_call(prompt, max_tokens) → str``.
- Has a 6-second timeout and a single retry on transient errors.
- Returns a graceful fallback message on any failure.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base for LLM service integrations."""

    provider_name: str = "base"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = (api_key or "").strip()
        self._available = bool(self._api_key)


    @property
    def is_available(self) -> bool:
        """``True`` when the provider has a non-empty API key configured."""
        return self._available

    async def explain_blocked_payment(
        self, reason: str, agent_name: str, merchant_name: str, amount: float,
    ) -> str:
        """Explain *why* a payment was blocked, in plain language.

        Returns a fixed fallback explanation when the provider is unavailable.
        """
        if not self.is_available:
            return _fallback_explain_blocked(reason, agent_name, merchant_name, amount)

        prompt = (
            f"A payment of {amount:.2f} from agent '{agent_name}' "
            f"to merchant '{merchant_name}' was BLOCKED.\n\n"
            f"Rejection reason: {reason}\n\n"
            "Explain this rejection in 1-2 plain-English sentences "
            "as if speaking to a non-technical owner.  "
            "Mention what rule was violated and what the owner can do about it.  "
            "Do NOT suggest giving the agent more money or lowering security.  "
            "Be concise."
        )

        return await self._safe_call(prompt, max_tokens=150)

    async def explain_policy(self, agent_name: str, policy: dict) -> str:
        """Summarise an agent's spending policy in plain language.

        *policy* is a dict with keys like ``per_transaction_limit``,
        ``daily_limit``, ``max_requests_per_minute``, ``balance``,
        ``status``.
        """
        if not self.is_available:
            return _fallback_explain_policy(agent_name, policy)

        prompt = (
            f"Agent '{agent_name}' has the following spending policy:\n\n"
            f"{_dict_to_bullets(policy)}\n\n"
            "Write 1-2 plain-English sentences summarising what this agent "
            "is allowed to do and what will block its payments.  "
            "Use the owner's perspective.  Be concise."
        )

        return await self._safe_call(prompt, max_tokens=150)

    async def summarize_audit(self, events: list[dict]) -> str:
        """Summarise recent audit-log activity in a human-readable paragraph.

        *events* is a list of dicts with ``event_type``, ``actor``,
        ``details``, ``timestamp``.
        """
        if not self.is_available:
            return _fallback_summarize_audit(events)

        recent = events[:20]
        lines = []
        for e in recent:
            dt = e.get("timestamp", "?")
            et = e.get("event_type", "?")
            actor = e.get("actor", "?")
            details = e.get("details", "")
            lines.append(f"- [{dt}] {et} by {actor}  details: {details}")

        prompt = (
            "Here is a recent audit log from the AgentPay Guard system:\n\n"
            + "\n".join(lines)
            + "\n\nSummarise the key activity in 1-2 plain-English paragraphs.  "
            "Highlight payments settled, payments blocked, and any administrative "
            "actions (freeze, unfreeze, policy changes).  Be concise."
        )

        return await self._safe_call(prompt, max_tokens=250)


    async def _safe_call(self, prompt: str, *, max_tokens: int) -> str:
        """Call the provider with a 6s timeout + 1 retry on transient errors.

        Returns a human-readable fallback string on any failure.
        """
        try:
            return await asyncio.wait_for(
                self._call_with_retry(prompt, max_tokens),
                timeout=6.0,
            )
        except asyncio.TimeoutError:
            logger.warning("%s API timed out after 6s", self.provider_name)
        except Exception:
            logger.exception("%s API call failed", self.provider_name)
        return "⚠️ AI explanation unavailable right now."

    async def _call_with_retry(self, prompt: str, max_tokens: int) -> str:
        """Try _call once, retry once on failure."""
        try:
            return await self._call(prompt, max_tokens)
        except Exception:
            logger.warning("%s first attempt failed, retrying…", self.provider_name)
            return await self._call(prompt, max_tokens)

    @abstractmethod
    async def _call(self, prompt: str, max_tokens: int) -> str:
        """Execute the actual API request.  Must be overridden."""
        ...




def _fallback_explain_blocked(
    reason: str, agent_name: str, merchant_name: str, amount: float,
) -> str:
    """Return a deterministic, plain-English explanation for a blocked payment."""
    explanations: dict[str, str] = {
        "AGENT_FROZEN": (
            f"Agent '{agent_name}' is currently frozen by the owner. "
            f"No payments can be processed until it is manually unfrozen."
        ),
        "MERCHANT_NOT_ALLOWED": (
            f"Merchant '{merchant_name}' is not on agent '{agent_name}'s "
            f"approved list. The owner can add it via the allowlist."
        ),
        "PER_TX_LIMIT_EXCEEDED": (
            f"The requested amount ({amount:.2f}) exceeds agent '{agent_name}'s "
            f"per-transaction limit. The owner can raise this limit in the "
            f"policy settings."
        ),
        "DAILY_LIMIT_EXCEEDED": (
            f"Accepting this payment of {amount:.2f} would exceed agent "
            f"'{agent_name}'s daily spending cap. The agent can retry "
            f"tomorrow, or the owner can increase the daily limit."
        ),
        "RATE_LIMIT_EXCEEDED": (
            f"Agent '{agent_name}' has sent too many requests in a short "
            f"period and has been rate-limited. It can retry after the "
            f"cool-down window."
        ),
        "DUPLICATE_REQUEST": (
            f"This exact payment request was already submitted (duplicate "
            f"request ID). No action is needed — this is an idempotency "
            f"rejection."
        ),
        "INSUFFICIENT_BALANCE": (
            f"Agent '{agent_name}' does not have enough balance to cover "
            f"{amount:.2f}. The owner can top up the simulated wallet."
        ),
    }
    return explanations.get(
        reason,
        f"Payment of {amount:.2f} from '{agent_name}' to '{merchant_name}' "
        f"was blocked. Reason: {reason}.",
    )


def _fallback_explain_policy(agent_name: str, policy: dict) -> str:
    """Return a deterministic policy summary."""
    parts = [f"Agent '{agent_name}' is {policy.get('status', '?').lower()}."]

    per_tx = policy.get("per_transaction_limit")
    if per_tx:
        parts.append(f"Each payment is capped at {per_tx:.2f}.")

    daily = policy.get("daily_limit")
    if daily:
        parts.append(f"Total daily spend cannot exceed {daily:.2f}.")

    rate = policy.get("max_requests_per_minute")
    if rate:
        parts.append(f"At most {rate} requests are allowed per minute.")

    balance = policy.get("balance")
    if balance is not None:
        parts.append(f"Current balance: {balance:.2f}.")

    return " ".join(parts)


def _fallback_summarize_audit(events: list[dict]) -> str:
    """Return a deterministic audit summary."""
    if not events:
        return "No audit events to summarise."

    total = len(events)
    settled = sum(1 for e in events if e.get("event_type") == "payment_settled")
    blocked = sum(1 for e in events if e.get("event_type") == "payment_blocked")
    frozen = sum(1 for e in events if e.get("event_type") == "agent_frozen")
    unfrozen = sum(1 for e in events if e.get("event_type") == "agent_unfrozen")

    parts = [f"Showing {total} recent audit events."]
    if settled:
        parts.append(f"{settled} payment(s) were settled.")
    if blocked:
        parts.append(f"{blocked} payment(s) were blocked.")
    if frozen:
        parts.append(f"{frozen} agent(s) were frozen.")
    if unfrozen:
        parts.append(f"{unfrozen} agent(s) were unfrozen.")
    return " ".join(parts)




def _dict_to_bullets(d: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in d.items())
