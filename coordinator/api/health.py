"""Health check and Prometheus metrics."""
from fastapi import APIRouter
from sqlalchemy import text

from cache import get_redis
from config import settings
from db.engine import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check with DB and Redis status."""
    db_ok = False
    redis_ok = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "service": settings.app_name,
        "checks": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }
