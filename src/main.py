import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.log import LOGGING_CONFIG

from src.graph.agent import lifespan_graph
from src.api.routers import router as chat_router

from src.config import settings

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LOG_LEVEL=%s", settings.LOG_LEVEL)
    logger.info("LLM_MODEL=%s", settings.OPENAI_MODEL)
    async with lifespan_graph(settings.DB_PATH) as graph:
        app.state.graph = graph
        yield


app = FastAPI(lifespan=lifespan, title=settings.APP_TITLE)


@app.get("/health")
async def health():
    return {"status": "ok"}


# router
app.include_router(chat_router)
