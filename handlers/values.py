# handlers/values.py

import functools
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import UserValue
from openai_validation import validate_value

router = Router()


async def save_value(user_id: int, value: str):
    async with AsyncSessionLocal() as session:
        new_value = UserValue(user_id=user_id, value=value)
        session.add(new_value)
        await session.commit()


@router.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    input_text = message.text
    message_timestamp = int(message.date.timestamp())
    await state.update_data(last_message_timestamp=message_timestamp, input_text=input_text)
    is_valid = await validate_value(input_text)
    print(f"Validation result for input '{input_text}': {is_valid}")

    if is_valid:
        await save_value(message.from_user.id, input_text)
        await message.answer("Ваши ключевые ценности успешно сохранены!")
    else:
        await message.answer("Пожалуйста, укажите корректные ключевые ценности.")


@router.callback_query(F.data == "define_values")
async def define_values(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Пожалуйста, укажите ваши ключевые ценности.")
    await callback_query.answer()
