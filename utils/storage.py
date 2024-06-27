import aiofiles
from aiogram import Bot
from aiogram.types import Voice
from config import config


async def save_voice_to_file(voice: Voice, bot: Bot) -> str:
    file_path = f"{config.audio_files_folder}/{voice.file_id}.ogg"
    async with aiofiles.open(file_path, 'wb') as out_file:
        await bot.download(voice, out_file)
    return file_path
