"""
FastAPI application entry point.

All routers are registered here. Run with:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logs.logger import get_logger
from src.api.router import health, history, query
from src.config.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown using the modern lifespan handler.

    Yields:
        None: Control returns to FastAPI while the app is running.
    """
    logger.info(
        "Started | app=%s | version=%s | model=%s | host=%s | port=%d",
        app.title,
        app.version,
        settings.groq_model,
        settings.api_host,
        settings.api_port,
    )
    yield
    logger.info("Shutdown | app=%s | version=%s", app.title, app.version)


app = FastAPI(
    title="MediQ Agent",
    description="Agentic AI system for medical Q&A using PubMed RAG and Groq LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(history.router)
