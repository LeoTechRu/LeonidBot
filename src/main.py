from fastapi import FastAPI
from src.core.lifespan import lifespan
from src.controllers.webhook import router as webhook_router
from src.admin import setup_admin

app = FastAPI(lifespan=lifespan)

# Register routers
app.include_router(webhook_router, prefix="/telegram-webhook")

# Setup admin panel
setup_admin(app)


@app.get("/")
def root():
    return {"status": "ok"}
