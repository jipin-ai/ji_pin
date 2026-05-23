"""Tongrui AI Secure Gateway — Coordinator Node.

FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.health import router as health_router
from api.nodes import router as nodes_router
from certs import generate_ca
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    # Startup: generate CA if not exists, init DB
    generate_ca()
    yield
    # Shutdown: close connections


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(nodes_router)

# CORS — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
