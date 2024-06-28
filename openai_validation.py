# openai_validation.py

from openai import OpenAI
import openai
from config import config
client = OpenAI(api_key=config.openai_api_key.get_secret_value())
from config import config



async def validate_value(input_text):
    response = await openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that validates user values."},
            {"role": "user", "content": f"Validate this value: {input_text}"}
        ]
    )
    validation = response['choices'][0]['message']['content'].strip().lower()
    return validation == "true"
