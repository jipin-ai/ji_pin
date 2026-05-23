"""Node health metrics."""

import os
import shutil


def get_load_avg() -> float:
    """Return 1-minute load average."""
    try:
        return os.getloadavg()[0]
    except (OSError, AttributeError):
        return 0.0


def get_disk_usage() -> float:
    """Return disk usage percent for root filesystem."""
    try:
        usage = shutil.disk_usage("/")
        return round((usage.used / usage.total) * 100, 1)
    except Exception:
        return 0.0


def get_memory_usage() -> dict:
    """Return memory stats in MB."""
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            if "MemTotal" in line:
                mem["total_mb"] = int(line.split()[1]) // 1024
            elif "MemAvailable" in line:
                mem["available_mb"] = int(line.split()[1]) // 1024
        mem["used_mb"] = mem.get("total_mb", 0) - mem.get("available_mb", 0)
        return mem
    except Exception:
        return {"total_mb": 0, "available_mb": 0, "used_mb": 0}


def collect_metrics() -> dict:
    return {
        "status": "healthy",
        "node_id": _try_get_node_id(),
        "load_avg": get_load_avg(),
        "disk_usage_pct": get_disk_usage(),
        "memory": get_memory_usage(),
    }


def _try_get_node_id() -> str:
    try:
        from main import get_node_id

        return get_node_id()
    except RuntimeError:
        return "unregistered"
