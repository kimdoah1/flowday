
from fastapi import FastAPI

app = FastAPI(title="AI Calendar API")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
