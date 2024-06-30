import logging
import requests
import os
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ContentType, CallbackQuery
from openai import OpenAI
from amplitude import Amplitude
from amplitude.event import BaseEvent
from concurrent.futures import ThreadPoolExecutor
import asyncio
import base64
from config import config

# Инициализация Amplitude
amplitude_api_key = config.amplitude_api_key.get_secret_value()
amplitude = Amplitude(amplitude_api_key)

# Создание единственного экземпляра ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=5)


class MoodStates(StatesGroup):
    waiting_for_photo = State()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


client = OpenAI(api_key=config.openai_api_key.get_secret_value())
router = Router()


async def analyze_photo(encoded_image: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{encoded_image}",
                        },
                        {
                            "type": "text",
                            "text": "Определи настроение человека на фото",
                        }
                    ]
                }
            ],
            max_tokens=1024,
        )

        mood = response.choices[0].message.content.strip().lower()
        return mood
    except Exception as e:
        logging.error(f"Error during mood analysis: {e}")
        return "Не удалось определить настроение"


def send_event(user_id: int, event_name: str, event_properties: dict):
    event = BaseEvent(
        user_id=str(user_id),
        event_type=event_name,
        event_properties=event_properties
    )
    amplitude.track(event)


@router.message(MoodStates.waiting_for_photo, F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

    # Скачивание файла
    file_response = requests.get(file_url)
    if file_response.status_code == 200:
        file_path = f"images/{file_id}.jpg"

        # Сохранение файла
        os.makedirs("images", exist_ok=True)
        with open(file_path, "wb") as file:
            file.write(file_response.content)

        # Шифрование файла
        encoded_image = encode_image(file_path)

        # Анализ фото
        mood = await analyze_photo(encoded_image)
        await message.answer(f"Ваше настроение: {mood}")

        # Отправка события в Amplitude
        loop = asyncio.get_event_loop()
        loop.run_in_executor(executor, send_event, message.from_user.id, "mood_detected", {"mood": mood})

        # Удаление файла после использования
        os.remove(file_path)
    else:
        await message.answer("Не удалось скачать фото. Попробуйте снова.")


@router.callback_query(F.data == "detect_mood")
async def detect_mood(callback_query: CallbackQuery, state: FSMContext):
    await state.set_state(MoodStates.waiting_for_photo)
    await callback_query.message.answer("Пожалуйста, отправьте фото, чтобы я мог определить ваше настроение.")
    await callback_query.answer()
