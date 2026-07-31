from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.messaging import consumers  # noqa: F401 — registers @broker.subscriber handlers
from app.messaging.broker import broker


@asynccontextmanager
async def lifespan(_: FastAPI):
    await broker.start()
    yield
    await broker.close()


# No HTTP routes: reports are requested over the message bus and downloaded
# through the backend, which checks job ownership. Serving files from here meant
# an unauthenticated endpoint that handed any user's export to any caller.
app = FastAPI(title="Wallet Report Service", lifespan=lifespan)
