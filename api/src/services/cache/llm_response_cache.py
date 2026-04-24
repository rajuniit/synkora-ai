"""
LLM Response Cache

Exact-match Redis cache for deterministic LLM responses.
Opt-in only (requires agent.performance_config.enable_response_cache = true).

Six correctness gates are enforced before any read or write:
  1. Opt-in:       Agent must have enable_response_cache = true  (checked by caller)
  2. Temperature:  temperature <= 0.1 only (near-deterministic)
  3. No tool ctx:  Skip if any message has role="tool"/"function" or tool_calls
  4. Time-sensit.: Skip if user message contains time-sensitive keywords
  5. Cache key:    SHA256(provider+model+temp_bucket+messages+system_hash+agent_updated_at)
                   — any agent edit changes agent_updated_at, auto-busts cache
  6. Size cap:     Skip storing responses > 50 KB
"""

import hashlib
import json
import logging

from src.config.redis import get_redis_async

logger = logging.getLogger(__name__)

LLM_RESPONSE_CACHE_TTL = 3600  # 1 hour
LLM_RESPONSE_CACHE_PREFIX = "llm_resp:"
MAX_CACHED_RESPONSE_BYTES = 50_000  # 50 KB

_TIME_SENSITIVE: frozenset[str] = frozenset(
    [
        "today",
        "tonight",
        "tomorrow",
        "yesterday",
        "now",
        "current",
        "currently",
        "latest",
        "recent",
        "this week",
        "this month",
        "this year",
        "right now",
        "at the moment",
        "as of",
        "breaking",
        "live",
        "real-time",
        "what time",
    ]
)


def _make_cache_key(
    provider: str,
    model_name: str,
    temperature: float,
    messages: list[dict],
    system_prompt_hash: str,
    agent_updated_at: str,
) -> str:
    temp_bucket = round(temperature * 10) / 10
    payload = json.dumps(
        {
            "p": provider,
            "m": model_name,
            "t": temp_bucket,
            "msgs": messages,
            "sp": system_prompt_hash,
            "av": agent_updated_at,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return LLM_RESPONSE_CACHE_PREFIX + digest


def _is_cacheable(messages: list[dict], temperature: float) -> bool:
    """Return False (skip cache) on any uncertainty — fails safe."""
    # Gate 2: temperature
    if temperature > 0.1:
        return False

    # Gate 3: tool context
    for msg in messages:
        if msg.get("role") in ("tool", "function"):
            return False
        if msg.get("tool_calls"):
            return False

    # Gate 4: time-sensitive content
    last_user = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
    )
    if isinstance(last_user, str):
        lower = last_user.lower()
        if any(kw in lower for kw in _TIME_SENSITIVE):
            return False

    return True


async def get_cached_response(
    provider: str,
    model_name: str,
    temperature: float,
    messages: list[dict],
    system_prompt_hash: str,
    agent_updated_at: str,
) -> str | None:
    """Return cached response string or None (fail-open on any error)."""
    if not _is_cacheable(messages, temperature):
        return None
    try:
        redis = get_redis_async()
        key = _make_cache_key(provider, model_name, temperature, messages, system_prompt_hash, agent_updated_at)
        value = await redis.get(key)
        if value:
            logger.debug(f"LLM response cache HIT: {key[:40]}...")
            return value.decode() if isinstance(value, bytes) else value
        return None
    except Exception as e:
        logger.debug(f"LLM response cache read error (fail-open): {e}")
        return None


async def set_cached_response(
    provider: str,
    model_name: str,
    temperature: float,
    messages: list[dict],
    response: str,
    system_prompt_hash: str,
    agent_updated_at: str,
) -> None:
    """Cache a response (fail-open on any error). Uses NX to prevent race overwrites."""
    if not _is_cacheable(messages, temperature):
        return
    # Gate 6: size cap
    if len(response.encode()) > MAX_CACHED_RESPONSE_BYTES:
        return
    try:
        redis = get_redis_async()
        key = _make_cache_key(provider, model_name, temperature, messages, system_prompt_hash, agent_updated_at)
        # NX = only set if not exists (atomic, prevents concurrent overwrites)
        await redis.set(key, response, ex=LLM_RESPONSE_CACHE_TTL, nx=True)
        logger.debug(f"LLM response cache SET: {key[:40]}...")
    except Exception as e:
        logger.debug(f"LLM response cache write error (fail-open): {e}")
