#!/usr/bin/env python3
"""
Clear rate limits for development testing.
This script removes rate limit entries from Redis.
"""
import asyncio
import redis.asyncio as aioredis
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings


async def clear_rate_limits(pattern: str = "*"):
    """Clear rate limit entries matching the pattern."""
    try:
        # Connect to Redis
        redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            encoding="utf-8",
            decode_responses=True
        )
        
        # Find all rate limit keys
        rate_limit_keys = []
        async for key in redis.scan_iter(match=f"rate_limit:{pattern}"):
            rate_limit_keys.append(key)
        
        if not rate_limit_keys:
            print("No rate limit keys found.")
            return
        
        print(f"Found {len(rate_limit_keys)} rate limit keys:")
        for key in rate_limit_keys[:10]:  # Show first 10
            print(f"  - {key}")
        if len(rate_limit_keys) > 10:
            print(f"  ... and {len(rate_limit_keys) - 10} more")
        
        # Ask for confirmation
        if input("\nClear these rate limits? (y/N): ").lower() == 'y':
            deleted = await redis.delete(*rate_limit_keys)
            print(f"Cleared {deleted} rate limit entries.")
        else:
            print("Cancelled.")
        
        await redis.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure Redis is running and accessible.")


async def clear_specific_ip(ip: str):
    """Clear rate limits for a specific IP address."""
    await clear_rate_limits(f"ip:{ip}:*")


async def clear_all_auth_endpoints():
    """Clear all rate limits for auth endpoints."""
    await clear_rate_limits("*:/api/v1/auth/*")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear rate limits from Redis")
    parser.add_argument("--ip", help="Clear limits for specific IP")
    parser.add_argument("--auth", action="store_true", help="Clear all auth endpoint limits")
    parser.add_argument("--all", action="store_true", help="Clear ALL rate limits")
    
    args = parser.parse_args()
    
    if args.ip:
        asyncio.run(clear_specific_ip(args.ip))
    elif args.auth:
        asyncio.run(clear_all_auth_endpoints())
    elif args.all:
        asyncio.run(clear_rate_limits("*"))
    else:
        # Default: clear auth endpoints
        print("Clearing auth endpoint rate limits...")
        asyncio.run(clear_all_auth_endpoints())