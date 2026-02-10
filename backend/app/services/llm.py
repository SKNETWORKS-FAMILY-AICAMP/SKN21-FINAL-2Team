import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True) # .env 로드

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_response(user_input: str, image: str | None = None, location: str | None = None) -> str:
    try:
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        
        user_content = []
        
        # Location Context
        if location:
            user_content.append({"type": "text", "text": f"Current Location: {location}\n"})

        # User Text
        user_content.append({"type": "text", "text": user_input})

        # Image
        if image:
            # Check if image header exists, if not add it
            image_url = image if image.startswith("data:") else f"data:image/jpeg;base64,{image}"
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
        
        messages.append({"role": "user", "content": user_content})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")
        return "죄송합니다. 오류가 발생했습니다."