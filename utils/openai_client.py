from openai import AsyncOpenAI, OpenAI

import dotenv
from config import config


# Получение идентификатора ассистента OpenAI
def get_assistant_id() -> str:
    if config.create_openai_assistant:
        assistant = OpenAI(api_key=config.openai_api_key.get_secret_value()).beta.assistants.create(
            name=config.openai_assistant_name,
            instructions=config.openai_assistant_instructions,
            model=config.openai_assistant_model
        )

        dotenv_file = dotenv.find_dotenv()
        dotenv.load_dotenv(dotenv_file)
        dotenv.set_key(dotenv_file, "OPENAI_ASSISTANT_ID", assistant.id)
        dotenv.set_key(dotenv_file, "CREATE_OPENAI_ASSISTANT", "False")

        return assistant.id
    else:
        return config.openai_assistant_id


client = AsyncOpenAI(api_key=config.openai_api_key.get_secret_value())
assistant_id = get_assistant_id()
