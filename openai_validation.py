import openai
from config import config

openai.api_key = config.openai_api_key.get_secret_value()


async def validate_value(input_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system",
                 "content": "Вы являетесь помощником, который проверяет, являются ли предоставленные значения ключевыми ценностями человека. Ответь «true», если значение допустимо, и «false», если нет."},
                {"role": "user",
                 "content": f"Проверьте значение: {input_text}. Ответьте 'true', если значение корректное и значимое, и 'false', если нет."}
            ]
        )

        # Добавляем отладочный вывод для проверки ответа
        print("OpenAI API response:", response)

        validation = response['choices'][0]['message']['content'].strip().lower()
        return validation == "true"
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

