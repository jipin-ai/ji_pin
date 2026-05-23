"""Redis integration — task queue, result cache, heartbeat state."""

import json

import redis.asyncio as aioredis

from config import settings

# Connection pool (lazy init)
_pool: aioredis.ConnectionPool | None = None


async def get_redis() -> aioredis.Redis:
    """Return a Redis connection from the pool."""
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return aioredis.Redis(connection_pool=_pool)


# ── Task Queue ──

TASK_QUEUE = "tr:task_queue"


async def enqueue_task(task_id: str, payload: dict) -> None:
    """Push a task onto the FIFO queue."""
    r = await get_redis()
    await r.lpush(TASK_QUEUE, json.dumps({"task_id": task_id, **payload}))


async def dequeue_task(timeout: int = 5) -> dict | None:
    """Pop a task from the queue (blocking)."""
    r = await get_redis()
    result = await r.brpop(TASK_QUEUE, timeout=timeout)
    if result is None:
        return None
    _, data = result
    return json.loads(data)  # type: ignore


async def queue_length() -> int:
    r = await get_redis()
    return await r.llen(TASK_QUEUE)  # type: ignore


# ── Result Cache ──


def _result_key(task_id: str) -> str:
    return f"tr:result:{task_id}"


async def cache_result(task_id: str, result: dict, ttl: int = 3600) -> None:
    """Store aggregated task result."""
    r = await get_redis()
    await r.setex(_result_key(task_id), ttl, json.dumps(result))


async def get_cached_result(task_id: str) -> dict | None:
    r = await get_redis()
    data = await r.get(_result_key(task_id))
    return json.loads(data) if data else None


# ── Heartbeat State ──


def _heartbeat_key(node_id: str) -> str:
    return f"tr:hb:{node_id}"


async def record_heartbeat(node_id: str, status: dict) -> None:
    """Cache latest heartbeat state in Redis (fast path)."""
    r = await get_redis()
    await r.setex(_heartbeat_key(node_id), 120, json.dumps(status))


async def get_heartbeat_state(node_id: str) -> dict | None:
    r = await get_redis()
    data = await r.get(_heartbeat_key(node_id))
    return json.loads(data) if data else None


# ── Node Status ──


def _node_status_key(node_id: str) -> str:
    return f"tr:node:{node_id}:status"


async def set_node_online(node_id: str) -> None:
    r = await get_redis()
    await r.set(_node_status_key(node_id), "ONLINE")


async def set_node_offline(node_id: str) -> None:
    r = await get_redis()
    await r.set(_node_status_key(node_id), "OFFLINE")


async def get_node_status(node_id: str) -> str | None:
    r = await get_redis()
    return await r.get(_node_status_key(node_id))
