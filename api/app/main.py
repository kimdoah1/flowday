from fastapi import FastAPI

from app.routers import plan


app = FastAPI(title="AI Calendar API")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


app.include_router(
    plan.router,
    prefix="/api",
    tags=["AI Plan"]
)