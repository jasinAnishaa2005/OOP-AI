from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin_exams, admin_topics, auth, exams, health, topics
from app.config import get_settings
from app.services.generation_worker import GenerationRecovery


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    recovery = GenerationRecovery() if get_settings().generation_recovery_enabled else None
    if recovery:
        recovery.start()
    yield
    if recovery:
        recovery.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(topics.router, prefix=settings.api_prefix)
    app.include_router(admin_topics.router, prefix=settings.api_prefix)
    app.include_router(exams.router, prefix=settings.api_prefix)
    app.include_router(admin_exams.router, prefix=settings.api_prefix)
    return app


app = create_app()
