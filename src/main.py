from fastapi import FastAPI, Request
from src.core.lifespan import lifespan
from src.controllers.webhook import router as webhook_router
from src.controllers.auth import router as auth_router

app = FastAPI(lifespan=lifespan)

app.include_router(webhook_router, prefix="/telegram-webhook")
app.include_router(auth_router)


@app.get("/")
def root():
    return {"status": "ok"}
