from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from database import AsyncSessionLocal
from models import UserValue
from openai import OpenAI
from config import config
import json

router = Router()

client = OpenAI(api_key=config.openai_api_key.get_secret_value())


class ValueStates(StatesGroup):
    waiting_for_values = State()


async def save_value(user_id: int, value: str):
    async with AsyncSessionLocal() as session:
        new_value = UserValue(user_id=user_id, value=value)
        session.add(new_value)
        await session.commit()


@router.message(ValueStates.waiting_for_values)
async def handle_message(message: Message, state: FSMContext):
    input_text = message.text
    user_id = message.from_user.id

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "Вы помощник, который определяет ключевые личные ценности в тексте и сохраняет их."},
                {"role": "user",
                 "content": f"Определите ключевые ценности в следующем тексте и сохраните их: {input_text}"}
            ],
            functions=[
                {
                    "name": "save_value",
                    "description": "Сохранить определенную ключевую ценность для пользователя",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "ID пользователя"
                            },
                            "value": {
                                "type": "string",
                                "description": "Ключевая ценность для сохранения"
                            }
                        },
                        "required": ["user_id", "value"]
                    }
                }
            ],
            function_call="auto"
        )
        print(response.choices[0].message)
        # Проверка, вызвана ли функция
        function_call = response.choices[0].message.function_call
        if function_call:
            if function_call.name == "save_value":
                arguments = json.loads(function_call.arguments)
                value = arguments["value"]
                await save_value(user_id, value)
                await message.answer(f"Ваша ключевая ценность '{value}' успешно сохранена!")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.")


@router.callback_query(F.data == "save_value")
async def define_values(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(mode="save_value")
    await state.set_state(ValueStates.waiting_for_values)
    await callback_query.message.answer("Пожалуйста, укажите ваши ключевые ценности.")
    await callback_query.answer()
