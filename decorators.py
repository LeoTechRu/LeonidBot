# /sd/tg/LeonidBot/decorators.py
from functools import wraps
from aiogram.types import Message
from services.telegram import UserService
from models import UserRole, GroupType
from logger import logger
from web.dependencies import get_session

def role_required(role: UserRole):
    """Декоратор для проверки прав доступа к командам"""
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: Message, *args, **kwargs):
            try:
                async with get_session() as session:
                    async with UserService(session) as user_service:
                        user, is_new = await user_service.get_or_create_user(
                            message.from_user.id,
                            username=message.from_user.username,
                            first_name=message.from_user.first_name,
                            last_name=message.from_user.last_name,
                            language_code=message.from_user.language_code,
                            is_premium=message.from_user.is_premium
                        )
                        if user.role >= role.value:
                            return await handler(message, *args, **kwargs)
                        await message.answer(f"Недостаточно прав. Требуется роль: {role.name}")
            except Exception as e:
                logger.error(f"Ошибка проверки роли: {e}")
                await message.answer("Произошла ошибка при проверке прав")
        return wrapper
    return decorator


async def group_required(handler):
    async def wrapper(message: Message, *args, **kwargs):
        try:
            async with get_session() as session:
                async with UserService(session) as user_service:
                    chat = message.chat
                    user_id = message.from_user.id
                    group_id = chat.id

                    # Используем get_or_create_group вместо дублирования
                    group, is_new = await user_service.get_or_create_group(
                        group_id,
                        title=chat.title,
                        type=GroupType(chat.type),
                        owner_id=user_id
                    )

                    is_member = await user_service.is_user_in_group(user_id, group_id)
                    if not is_member:
                        success, response = await user_service.add_user_to_group(user_id, group_id)
                        if not success:
                            await message.answer(f"Не удалось добавить вас в группу: {response}")
                            return

                    return await handler(message, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка проверки группы: {e}")
            await message.answer("Произошла ошибка при проверке членства в группе")

    return wrapper
