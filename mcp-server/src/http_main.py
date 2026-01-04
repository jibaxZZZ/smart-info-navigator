"""HTTP entrypoint for running the MCP server over streamable HTTP."""

from __future__ import annotations

import uvicorn

from .config import settings
from .http_app import create_app
from .utils.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    logger.info(f"Starting HTTP server for {settings.app_name} v{settings.app_version}")
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()