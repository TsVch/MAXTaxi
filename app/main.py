from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.webhook import mock_router, router
from app.core.database import Base, engine
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MAX Taxi Chatbot Backend", lifespan=lifespan)
app.include_router(router)
app.include_router(mock_router)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
