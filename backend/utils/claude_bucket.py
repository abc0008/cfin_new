"""
Claude API rate limiting utility using token bucket pattern.
"""
import asyncio
import time
import logging
from typing import Dict

log = logging.getLogger(__name__)

class ClaudeBucket:
    """
    Token bucket implementation for Claude API rate limiting.
    Uses response headers from Claude to implement graceful backoff.
    """
    _reset_ts = 0.0
    _tokens_remaining = 999_999

    @classmethod
    async def throttle(cls, need: int):
        """
        Check if we need to wait before making a request requiring 'need' tokens.
        
        Args:
            need: Number of tokens needed for the request
        """
        now = time.time()
        wait = max(0, cls._reset_ts - now) if cls._tokens_remaining < need else 0
        if wait:
            log.info("Sleeping %.2f s for Claude rate-limit", wait)
            await asyncio.sleep(wait)

    @classmethod
    def update(cls, headers: Dict[str, str]):
        """
        Update rate limit state from Claude response headers.
        
        Args:
            headers: Response headers from Claude API
        """
        try:
            cls._tokens_remaining = int(headers.get("anthropic-ratelimit-tokens-remaining",
                                                  cls._tokens_remaining))
            reset_in = float(headers.get("anthropic-ratelimit-tokens-reset", 0))
            cls._reset_ts = time.time() + reset_in
        except (ValueError, TypeError):
            # If headers are malformed, keep existing values
            pass 