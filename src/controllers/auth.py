from fastapi import APIRouter, Body

from services.telegram import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/telegram")
async def auth_telegram(data: dict = Body(...)):
    async with UserService() as user_service:
        await user_service.get_or_create_by_login_data(data)
    return {"status": "ok"}
