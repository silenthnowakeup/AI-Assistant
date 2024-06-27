from aiofiles import os

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Voice, FSInputFile

from config import config
from utils.openai_client import client, assistant_id

router = Router()


async def save_voice_message(voice: Voice, bot: Bot) -> str:
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


async def response(text: str, state, message_timestamp: int):
    state_data = await state.get_data()

    # Displaying "waiting" message
    waiting_message = await state.bot.send_message(state.chat.id, "Processing...")

    if "last_message_timestamp" in state_data and (
            message_timestamp - state_data["last_message_timestamp"]) <= config.thread_lifetime_sec:
        thread_id = state_data["thread_id"]
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

    # Deleting "waiting" message
    await state.bot.delete_message(chat_id=state.chat.id, message_id=waiting_message.id)

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


@router.message(F.voice)
async def voice_handler(message: Message, bot: Bot, state: FSMContext):
    voice_file_path = await save_voice_message(message.voice, bot)
    voice_text = await transcription(voice_file_path)
    message_timestamp = int(message.date.timestamp())
    response_messages, thread_id = await response(voice_text, state, message_timestamp)
    response_files_paths = await parse_messages_to_voices(response_messages, thread_id)
    for response_file_path in response_files_paths:
        await message.answer_voice(FSInputFile(response_file_path))
        await os.remove(response_file_path)
    await state.update_data(last_message_timestamp=message_timestamp)


@router.message(F.text)
async def text_handler(message: Message, state):
    text = message.text
    message_timestamp = int(message.date.timestamp())
    response_messages, thread_id = await response(text, state, message_timestamp)
    response_texts = [msg["text"] for msg in response_messages]
    response_text = "\n".join(response_texts)
    await message.answer(response_text)
    await state.update_data(last_message_timestamp=message_timestamp)
