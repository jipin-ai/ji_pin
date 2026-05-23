"""Gateway node — FastAPI entry point.

On startup:
  1. Register with coordinator
  2. Start heartbeat loop
  3. Start task poller
"""

import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config import settings
from health import collect_metrics

_client: httpx.AsyncClient | None = None
_node_id: str | None = None
_tasks: list[asyncio.Task] = []


def get_node_id() -> str:
    if _node_id is None:
        raise RuntimeError("Node not registered yet")
    return _node_id


async def _register():
    global _client, _node_id
    _client = httpx.AsyncClient(timeout=10)
    resp = await _client.post(
        f"{settings.coordinator_url}/api/v1/nodes/register",
        json={"name": settings.node_name, "org_name": settings.org_name},
    )
    resp.raise_for_status()
    data = resp.json()
    _node_id = data["node_id"]
    print(f"[node] Registered as {_node_id}", flush=True)


async def _start_background():
    from heartbeat import heartbeat_loop, task_poller

    assert _client is not None
    assert _node_id is not None
    _tasks.append(asyncio.create_task(heartbeat_loop(_client)))
    _tasks.append(asyncio.create_task(task_poller(_client, _node_id)))
    print("[node] Background tasks started", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _register()
    await _start_background()
    yield
    for t in _tasks:
        t.cancel()
    if _client:
        await _client.aclose()


app = FastAPI(
    title="Tongrui Gateway Node",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return collect_metrics()


@app.get("/local/v1/health")
async def local_health():
    return collect_metrics()
