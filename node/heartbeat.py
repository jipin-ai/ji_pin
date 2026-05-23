"""Heartbeat + task polling loop."""

import asyncio
import time

from config import settings
from health import get_load_avg, get_disk_usage


async def heartbeat_loop(client):
    """Send heartbeat to coordinator every N seconds."""
    node_id = None
    while node_id is None:
        await asyncio.sleep(0.5)
        try:
            from main import get_node_id

            node_id = get_node_id()
        except RuntimeError:
            pass

    while True:
        try:
            resp = await client.post(
                f"{settings.coordinator_url}/api/v1/nodes/{node_id}/heartbeat",
                json={
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "healthy",
                    "load_avg": get_load_avg(),
                    "disk_usage": get_disk_usage(),
                    "active_tasks": 0,
                },
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[heartbeat] Failed: {e}", flush=True)

        await asyncio.sleep(settings.heartbeat_interval)


async def task_poller(client, node_id: str):
    """Poll coordinator for pending tasks."""
    while True:
        try:
            resp = await client.get(
                f"{settings.coordinator_url}/api/v1/nodes/{node_id}/tasks/pending",
            )
            resp.raise_for_status()
            data = resp.json()
            for task in data.get("tasks", []):
                print(f"[poller] Received task: {task.get('task_id', 'unknown')}")
                # V1.0: placeholder — task execution in M5
        except Exception as e:
            print(f"[poller] Failed: {e}")

        await asyncio.sleep(5)
