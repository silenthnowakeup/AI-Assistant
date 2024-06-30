from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from database import AsyncSessionLocal
from models import UserValue
from openai import OpenAI
from config import config

client = OpenAI(api_key=config.openai_api_key.get_secret_value())
router = Router()

class ValueStates(StatesGroup):
    waiting_for_values = State()

async def validate_value(input_text):
    try:
        response = client.chat.completions.create(model="gpt-4o",
                                                  messages=[
                                                      {"role": "system",
                                                       "content": "Вы являетесь помощником, который проверяет, являются ли предоставленные значения ключевыми ценностями человека. Ответь «true», если значение допустимо, и «false», если нет."},
                                                      {"role": "user",
                                                       "content": f"Проверьте значение: {input_text}. Ответьте 'true', если значение корректное и значимое, и 'false', если нет."}
                                                  ])

        validation = response.choices[0].message.content.strip().lower()
        return validation == "true"
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


async def save_value(user_id: int, value: str):
    async with AsyncSessionLocal() as session:
        new_value = UserValue(user_id=user_id, value=value)
        session.add(new_value)
        await session.commit()


@router.message(ValueStates.waiting_for_values)
async def handle_message(message: Message, state: FSMContext):
    state_data = await state.get_data()
    if state_data.get('mode') == 'define_values':
        input_text = message.text
        message_timestamp = int(message.date.timestamp())
        await state.update_data(last_message_timestamp=message_timestamp, input_text=input_text)
        is_valid = await validate_value(input_text)
        if is_valid:
            await save_value(message.from_user.id, input_text)
            await message.answer("Ваши ключевые ценности успешно сохранены!")
        else:
            await message.answer("Пожалуйста, укажите корректные ключевые ценности.")


@router.callback_query(F.data == "define_values")
async def define_values(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(mode="define_values")
    await state.set_state(ValueStates.waiting_for_values)
    await callback_query.message.answer("Пожалуйста, укажите ваши ключевые ценности.")
    await callback_query.answer()
