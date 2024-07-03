import logging
from aiofiles import os
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Voice, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import config
from aiogram.enums import ContentType
from aiogram.fsm.state import StatesGroup, State
from utils.openai_client import client, assistant_id
import asyncio
import os

router = Router()
logger = logging.getLogger(__name__)


class AssistantStates(StatesGroup):
    active = State()


async def save_voice_message(voice: Voice, bot: Bot) -> str:
    os.makedirs(config.audio_files_folder, exist_ok=True)
    file_path = f"{config.audio_files_folder}/{voice.file_id}.ogg"
    await bot.download(voice, file_path)
    return file_path


async def transcription(file_path: str) -> str:
    with open(file_path, "rb") as voice_file:
        transcription = await client.audio.transcriptions.create(
            model=config.openai_stt_model,
            file=voice_file
        )
    await os.remove(file_path)
    return transcription.text


async def response(text: str, state: FSMContext, message_timestamp: int):
    state_data = await state.get_data()
    thread_id = state_data.get("thread_id")
    if thread_id and ((message_timestamp - state_data["last_message_timestamp"]) <= config.thread_lifetime_sec):
        pass
    else:
        thread = await client.beta.threads.create()
        thread_id = thread.id
        await state.update_data(thread_id=thread_id)
    message = await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )
    user_message_id = message.id
    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    raw_messages = await client.beta.threads.messages.list(
        thread_id=thread_id,
        order="asc",
        after=user_message_id
    )
    messages = [{"id": raw_message.id, "text": raw_message.content[0].text.value} for raw_message in raw_messages.data]
    return messages, thread_id


async def parse_messages_to_voices(messages, thread_id: str):
    files_paths = []
    for message in messages:
        file_path = f"{config.audio_files_folder}/{thread_id}_{message['id']}.mp3"
        files_paths.append(file_path)
        response = await client.audio.speech.create(
            model=config.openai_tts_model,
            voice=config.openai_tts_voice,
            input=message["text"]
        )
        response.stream_to_file(file_path)
    return files_paths


@router.message(AssistantStates.active, F.content_type == ContentType.TEXT)
async def text_handler(message: Message, state: FSMContext):
    print("1")
    state_data = await state.get_data()
    if state_data.get('mode') == 'assistant':
        logger.info("Handling text message in assistant mode")
        input_text = message.text
        message_timestamp = int(message.date.timestamp())
        await state.update_data(last_message_timestamp=message_timestamp, input_text=input_text)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ответ текстом", callback_data="text_response")],
            [InlineKeyboardButton(text="Ответ голосом", callback_data="voice_response")]
        ])
        await message.answer("Как вы хотите получить ответ?", reply_markup=markup)
    else:
        logger.info("Received text message but not in assistant mode")


@router.message(AssistantStates.active, F.content_type == ContentType.VOICE)
async def voice_handler(message: Message, bot: Bot, state: FSMContext):
    state_data = await state.get_data()
    if state_data.get('mode') == 'assistant':
        logger.info("Handling voice message in assistant mode")
        voice_file_path = await save_voice_message(message.voice, bot)
        voice_text = await transcription(voice_file_path)
        message_timestamp = int(message.date.timestamp())
        await state.update_data(last_message_timestamp=message_timestamp, input_text=voice_text)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ответ текстом", callback_data="text_response")],
            [InlineKeyboardButton(text="Ответ голосом", callback_data="voice_response")]
        ])
        await message.answer("Как вы хотите получить ответ?", reply_markup=markup)


@router.callback_query(F.data.in_({"text_response", "voice_response"}))
async def process_callback(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    logger.info("Processing callback query")
    data = callback_query.data
    state_data = await state.get_data()
    input_text = state_data.get('input_text', '')
    message_timestamp = state_data.get('last_message_timestamp', int(callback_query.message.date.timestamp()))
    response_messages, thread_id = await response(input_text, state, message_timestamp)
    if data == "text_response":
        response_texts = [msg["text"] for msg in response_messages]
        response_text = "\n".join(response_texts)
        await callback_query.message.answer(response_text)
    elif data == "voice_response":
        os.makedirs(config.audio_files_folder, exist_ok=True)
        response_files_paths = await parse_messages_to_voices(response_messages, thread_id)
        for response_file_path in response_files_paths:
            await callback_query.message.answer_voice(FSInputFile(response_file_path))
            os.remove(response_file_path)
    await state.update_data(last_message_timestamp=message_timestamp)
    await callback_query.answer()
    await asyncio.sleep(1)
    try:
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")


def register_handlers(dp):
    dp.include_routers(router)


@router.callback_query(F.data == "assistant_response")
async def assistant_response(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(mode="assistant")
    await state.set_state(AssistantStates.active)
    await callback_query.message.answer("Теперь вы можете отправлять сообщения виртуальному ассистенту.")
    await callback_query.answer()
