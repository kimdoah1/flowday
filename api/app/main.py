from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import initialize
from app.routers import events, proposals, extract, meetings

from app.routers import plan


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="AI Calendar API", lifespan=lifespan)
app.include_router(events.router)
app.include_router(proposals.router)
app.include_router(extract.router, prefix="/api")
app.include_router(meetings.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


app.include_router(
    plan.router,
    prefix="/api",
    tags=["AI Plan"]
)
