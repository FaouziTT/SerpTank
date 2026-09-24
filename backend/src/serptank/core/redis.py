"""Redis client factory. Credentials and TLS come from ``SERPTANK_REDIS_URL``.

Values are stored as strings/JSON only - never pickled (the legacy cache used
``pickle.loads`` on Redis data, an RCE vector if Redis is reachable).
"""

from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis

from serptank.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis
