import logging
import pathlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.config import get_settings
from app.db.engine import _async_session_factory
from app.providers import get_embedding_provider, get_llm_provider
from app.rag.ingest import ingest_all
from app.runner import init_runner

logger = logging.getLogger(__name__)

CONTENT_ROOT = pathlib.Path("/app/content")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    llm_provider = get_llm_provider(settings)
    embedder = get_embedding_provider(settings)
    init_runner(llm_provider, settings, embedder)
    async with _async_session_factory() as session:
        report = await ingest_all(session, CONTENT_ROOT, embedder)
    logger.info(report.summary())
    yield


app = FastAPI(title="Unscripted Backend", version="0.1.0", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allowed_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
