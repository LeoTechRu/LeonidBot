from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date

from core.services.nexus_service import HabitService

router = Router()


class HabitAddStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_frequency = State()


@router.message(Command("habit_list"))
async def habit_list(message: Message):
    async with HabitService() as habit_service:
        habits = await habit_service.list(owner_id=message.from_user.id)
    if not habits:
        await message.answer("У вас пока нет привычек.")
        return
    lines = []
    for habit in habits:
        metrics = habit.metrics or {}
        progress_data = metrics.get("progress", {})
        percent = 0
        if isinstance(progress_data, dict):
            total = len(progress_data)
            completed = sum(1 for v in progress_data.values() if v)
            percent = int(completed / total * 100) if total else 0
        elif isinstance(progress_data, list):
            total = len(progress_data)
            percent = int(total / total * 100) if total else 0
        elif isinstance(progress_data, (int, float)):
            percent = int(progress_data)
        lines.append(f"{habit.id}. {habit.name} — {percent}%")
    await message.answer("\n".join(lines))


@router.message(Command("habit_add"))
async def habit_add(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=2)
    if len(parts) >= 3:
        name, frequency = parts[1], parts[2]
        await _create_habit(message, name, frequency)
        return
    if len(parts) == 2:
        await state.update_data(name=parts[1])
        await message.answer("Укажите частоту привычки:")
        await state.set_state(HabitAddStates.waiting_for_frequency)
    else:
        await message.answer("Введите название привычки:")
        await state.set_state(HabitAddStates.waiting_for_name)


@router.message(HabitAddStates.waiting_for_name)
async def habit_add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Укажите частоту привычки:")
    await state.set_state(HabitAddStates.waiting_for_frequency)


@router.message(HabitAddStates.waiting_for_frequency)
async def habit_add_frequency(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    frequency = message.text.strip()
    await _create_habit(message, name, frequency)
    await state.clear()


async def _create_habit(message: Message, name: str, frequency: str) -> None:
    async with HabitService() as habit_service:
        habit = await habit_service.create(
            owner_id=message.from_user.id,
            name=name,
            metrics={"frequency": frequency, "progress": {}},
        )
    await message.answer(
        f"Привычка '{habit.name}' создана с частотой '{frequency}'."
    )


@router.message(Command("habit_done"))
async def habit_done(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используйте: /habit_done <habit_id>")
        return
    habit_id = int(parts[1])
    async with HabitService() as habit_service:
        success = await habit_service.toggle_progress(habit_id, date.today())
    if success:
        await message.answer("Отмечено как выполненное на сегодня.")
    else:
        await message.answer("Привычка не найдена.")
