# openai_validation.py

import openai
from config import config

openai.api_key = config.openai_api_key


async def validate_value(value: str) -> bool:
    response = await openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Validate the following value for correctness: '{value}'. Is it a valid value? Respond with 'True' or 'False'.",
        max_tokens=5,
        temperature=0
    )
    result = response.choices[0].text.strip()
    return result.lower() == "true"
