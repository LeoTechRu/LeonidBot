# /sd/tg/LeonidBot/bot/handlers/telegram.py
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from typing import Callable
from decorators import role_required
from core.models import GroupType, LogLevel, UserRole
from core.services.telegram_user_service import TelegramUserService

# ==============================
# РОУТЕРЫ
# ==============================
router = Router()
user_router = Router()
group_router = Router()

# -----------------------------
# Универсальные функции
# -----------------------------

async def process_data_input(
    message: Message,
    state: FSMContext,
    validation_func: Callable,
    update_method: Callable,
    success_msg: str,
    error_msg: str
):
    """Универсальный обработчик ввода данных через FSM"""
    data = message.text.strip()
    if not validation_func(data):
        await message.answer(error_msg)
        return

    async with TelegramUserService() as user_service:
        success = await update_method(user_service, message.from_user.id, data)

    if success:
        await message.answer(success_msg.format(data=data))
    else:
        await message.answer("Произошла ошибка при сохранении данных")
    await state.clear()

# -----------------------------
# Валидаторы
# -----------------------------

def validate_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]

def validate_phone(phone: str) -> bool:
    return phone.startswith("+") and phone[1:].isdigit()

def validate_birthday(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def validate_group_description(desc: str) -> bool:
    return len(desc) <= 500

def validate_fullname(name: str) -> bool:
    return 0 < len(name) <= 100

# -----------------------------
# Состояния FSM
# -----------------------------

class UpdateDataStates(StatesGroup):
    waiting_for_birthday = State()
    waiting_for_email = State()
    waiting_for_fullname = State()
    waiting_for_phone = State()
    waiting_for_group_description = State()

# -----------------------------
# Команды
# -----------------------------
@router.message(Command("start"))
@user_router.message(F.text.lower().in_(["старт", "start", "привет", "hello"]))
async def cmd_start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Добро пожаловать в бота.")

@user_router.message(Command("cancel"))
@user_router.message(F.text.lower().in_(["cancel", "отмена", "выйти", "прервать"]))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer(f"{message.from_user.first_name}, ввод отменен.")
    else:
        await message.answer(f"{message.from_user.first_name}, вы не находитесь в режиме ввода.")

@user_router.message(Command("birthday"))
@user_router.message(F.text.lower() == "день рождение")
async def cmd_birthday(message: Message, state: FSMContext):
    async with TelegramUserService() as user_service:
        user_db = await user_service.get_user_by_telegram_id(message.from_user.id)
        if user_db and user_db.birthday:
            today = datetime.today().date()
            this_year_birthday = user_db.birthday.replace(year=today.year)
            if this_year_birthday < today:
                this_year_birthday = this_year_birthday.replace(year=today.year + 1)
            days_left = (this_year_birthday - today).days
            if days_left == 0:
                await message.answer(f"{message.from_user.first_name}, сегодня ваш день рождения! 🎉 ({user_db.birthday.strftime('%d.%m.%Y')})")
            else:
                await message.answer(f"{message.from_user.first_name}, до дня рождения осталось {days_left} дней ({user_db.birthday.strftime('%d.%m.%Y')})")
        else:
            await message.answer(f"{message.from_user.first_name}, введите ваш день рождения в формате ДД.ММ.ГГГГ:")
            await state.set_state(UpdateDataStates.waiting_for_birthday)

@user_router.message(Command("contact"))
@user_router.message(F.text.lower().in_(["контакт", "профиль"]))
async def cmd_contact(message: Message):
    async with TelegramUserService() as user_service:
        info = await user_service.get_contact_info(message.from_user.id)

    if not info:
        await message.answer(
            f"{message.from_user.first_name}, произошла ошибка при получении данных"
        )
        return

    name = (
        info.get("full_display_name")
        or f"{info.get('first_name') or ''} {info.get('last_name') or ''}".strip()
        or message.from_user.first_name
    )

    fields = {
        "Telegram ID": info["telegram_id"],
        "Username": info.get("username"),
        "Имя": name,
        "Email": info.get("email"),
        "Телефон": info.get("phone"),
        "День рождения": info.get("birthday"),
    }

    lines = [f"{name}, контактные данные:"]
    for label, value in fields.items():
        if value:
            lines.append(f"{label}: {value}")

    lines.append("")
    lines.append("Команды для обновления:")
    lines.append("/setfullname - установить отображаемое имя")
    lines.append("/setemail - установить email")
    lines.append("/setphone - установить телефон")
    lines.append("/setbirthday - установить день рождения")

    await message.answer("\n".join(lines))


@user_router.message(Command("setfullname"))
async def cmd_set_fullname(message: Message, state: FSMContext):
    await message.answer("Введите отображаемое имя:")
    await state.set_state(UpdateDataStates.waiting_for_fullname)


@user_router.message(UpdateDataStates.waiting_for_fullname)
async def process_fullname(message: Message, state: FSMContext):
    await process_data_input(
        message,
        state,
        validate_fullname,
        TelegramUserService.update_full_display_name,
        "Имя обновлено: {data}",
        "Имя должно быть непустым и не длиннее 100 символов",
    )

# -----------------------------
# Группы
# -----------------------------

@group_router.message(Command("group"))
@group_router.message(F.text.lower().in_(["группа", "group"]))
async def cmd_group(message: Message):
    async with TelegramUserService() as user_service:
        chat = message.chat
        chat_title = chat.title or f"{message.from_user.first_name} группа"
        group = await user_service.get_group_by_telegram_id(chat.id)
        if not group:
            group = await user_service.create_group(
                telegram_id=chat.id,
                title=chat.title or chat_title,
                type=GroupType(chat.type.lower()),
                owner_id=message.from_user.id
            )
            await message.answer(f"Группа '{chat_title}' добавлена в БД. Вы — её создатель.")
            return
        is_member = await user_service.is_user_in_group(message.from_user.id, chat.id)
        if not is_member:
            success, response = await user_service.add_user_to_group(message.from_user.id, chat.id)
            await message.answer(response if success else f"Ошибка: {response}")
            return
        members = await user_service.get_group_members(chat.id)
        if members:
            member_list = "\n".join([m.full_display_name or m.first_name for m in members])
            await message.answer(f"Участники группы '{chat_title}':\n{member_list}")
        else:
            await message.answer("Группа пока пуста.")

# -----------------------------
# Логирование
# -----------------------------

@user_router.message(Command("setloglevel"))
@role_required(UserRole.admin)  # Добавьте проверку прав администратора
async def cmd_set_log_level(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Используйте: /setloglevel [level]")
        return
    level = parts[1].upper()
    if level not in ["DEBUG", "INFO", "ERROR"]:
        await message.answer("Недопустимый уровень: используйте DEBUG, INFO или ERROR")
        return
    async with TelegramUserService() as user_service:
        # ``LogLevel`` теперь основан на ``IntEnum``, поэтому преобразуем
        # строковое имя уровня через обращение по ключу.
        success = await user_service.update_log_level(
            LogLevel[level], chat_id=message.chat.id
        )
        if success:
            await message.answer(f"Уровень логирования установлен: {level}")
        else:
            await message.answer("Не удалось обновить настройки логирования")

@user_router.message(Command("getloglevel"))
async def cmd_get_log_level(message: Message):
    async with TelegramUserService() as user_service:
        log_settings = await user_service.get_log_settings()
        current_level = log_settings.level if log_settings else LogLevel.ERROR
        chat_id = log_settings.chat_id if log_settings else "не задан"
        await message.answer(f"Текущий уровень: {current_level}\nГруппа для логов: {chat_id}")

# Универсальный хендлер (ловит всё, что не подошло выше)
log_chat_id = -1002662867876
@router.message(F.chat.id != log_chat_id)
async def unknown_message_handler(message: Message):
    try:
        # Добавляем метаданные в текст сообщения
        meta_text = f"||origin_chat_id:{message.chat.id}|origin_msg_id:{message.message_id}||"
        await message.forward(log_chat_id)
        # Отправляем метаданные как отдельное сообщение (скрытое)
        from core.db import bot
        await bot.send_message(log_chat_id, meta_text, parse_mode=None)
    except Exception as e:
        print(f"Ошибка логирования: {e}")

@router.message(F.chat.id == log_chat_id)
async def handle_admin_reply(message: Message):
    from core.db import bot
    from aiogram.exceptions import TelegramAPIError
    from core.logger import logger
    if message.reply_to_message:
        # Ищем метаданные в тексте ответа или в reply_to_message
        meta_match = re.search(r"\|\|origin_chat_id:(\d+)\|origin_msg_id:(\d+)\|\|", message.reply_to_message.text)
        if meta_match:
            origin_chat_id = int(meta_match.group(1))
            origin_msg_id = int(meta_match.group(2))
            # Отправляем ответ пользователю
            try:
                await bot.send_message(origin_chat_id, f"{message.text}")
            except TelegramAPIError as e:
                logger.error(f"Не удалось отправить ответ пользователю: {e}")
