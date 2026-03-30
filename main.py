from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from routes.api.v1 import api_v1_router
from settings import get_settings
from utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    _log_provider_status(settings)
    logger.info("GlowAPI starting up")
    yield
    logger.info("GlowAPI shutting down")


def _log_provider_status(settings) -> None:
    has_github = bool(
        settings.github_client_id
        and settings.github_app_installation_id
        and settings.github_app_private_key
    )
    has_bitbucket = bool(settings.bitbucket_workspace_token)

    if has_github:
        logger.info("GitHub provider: configured")
    else:
        logger.warning("GitHub provider: not configured — GitHub repos will fail at request time")

    if has_bitbucket:
        logger.info("Bitbucket provider: configured")
    else:
        logger.warning("Bitbucket provider: not configured — Bitbucket repos will fail at request time")

    if not has_github and not has_bitbucket:
        logger.warning("No git provider configured. Set credentials before handling requests.")


app = FastAPI(
    title="GlowAPI",
    description=(
        "Turn your GitOps repo into an API. "
        "Programmatically create config files, open PRs, and receive status callbacks "
        "without bypassing your existing review workflow."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/healthcheck", tags=["Health"])
async def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "main:app",
        host=s.app_host,
        port=s.app_port,
        workers=s.app_workers,
        reload=s.app_reload,
        access_log=s.app_access_logs,
    )
