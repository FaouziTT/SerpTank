#!/usr/bin/env python3
"""
Clear login attempt counters from Redis.
"""
import asyncio
import redis.asyncio as aioredis
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings


async def clear_login_attempts():
    """Clear all login attempt counters."""
    try:
        # Connect to Redis
        redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            encoding="utf-8",
            decode_responses=True
        )
        
        # Find all login attempt keys
        login_attempt_keys = []
        async for key in redis.scan_iter(match="login_attempts:*"):
            login_attempt_keys.append(key)
        
        # Also find failed login keys
        async for key in redis.scan_iter(match="failed_logins:*"):
            login_attempt_keys.append(key)
        
        if not login_attempt_keys:
            print("No login attempt keys found.")
            return
        
        print(f"Found {len(login_attempt_keys)} login attempt keys:")
        for key in login_attempt_keys:
            value = await redis.get(key)
            print(f"  - {key}: {value} attempts")
        
        # Clear all keys
        deleted = await redis.delete(*login_attempt_keys)
        print(f"\nCleared {deleted} login attempt entries.")
        
        await redis.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure Redis is running and accessible.")


if __name__ == "__main__":
    print("Clearing login attempt counters...")
    asyncio.run(clear_login_attempts())