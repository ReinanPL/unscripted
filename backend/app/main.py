from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.config import get_settings
from app.providers import get_llm_provider
from app.runner import init_runner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    provider = get_llm_provider(settings)
    init_runner(provider, settings)
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
