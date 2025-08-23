from fastapi import FastAPI
from .routes import admin, auth, index

app = FastAPI()
app.include_router(index.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(admin.router, prefix="/admin")
