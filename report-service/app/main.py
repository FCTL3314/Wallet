from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.messaging import consumers  # noqa: F401 — registers @broker.subscriber handlers
from app.messaging.broker import broker
from app.reports.router import router as reports_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await broker.start()
    yield
    await broker.close()


app = FastAPI(title="Wallet Report Service", lifespan=lifespan)
app.include_router(reports_router)
