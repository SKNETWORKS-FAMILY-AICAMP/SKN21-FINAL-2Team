import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True) # .env 로드

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_response(user_input: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")
        return "죄송합니다. 오류가 발생했습니다."