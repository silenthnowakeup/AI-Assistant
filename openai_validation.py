# openai_validation.py

from openai import OpenAI
from config import config
client = OpenAI(api_key=config.openai_api_key.get_secret_value())
from config import config



async def validate_value(value: str) -> bool:
    response = await client.completions.create(model="text-davinci-003",
    prompt=f"Validate the following value for correctness: '{value}'. Is it a valid value? Respond with 'True' or 'False'.",
    max_tokens=5,
    temperature=0)
    result = response.choices[0].text.strip()
    return result.lower() == "true"
