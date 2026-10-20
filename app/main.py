from fastapi import FastAPI

from app.api.webhook import router as webhook_router


app = FastAPI(
    title="Jingtorls AI Web Studio Messenger API",
    description="Backend for the Jingtorls AI Web Studio Messenger automation system.",
    version="1.0.0",
)


app.include_router(webhook_router)


@app.get("/")
async def root():
    return {
        "service": "Jingtorls AI Web Studio Messenger API",
        "status": "online",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
    }
