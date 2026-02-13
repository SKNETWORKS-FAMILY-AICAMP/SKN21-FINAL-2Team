import os
from openai import OpenAI
from dotenv import load_dotenv
from app.services.prompts import PROMPTS

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_response(user_input: str, image: str | None = None, location: str | None = None, context: str | None = None) -> str:
    try:
        messages = [{"role": "system", "content": PROMPTS}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "아래 CONTEXT INFORMATION을 최우선 근거로 사용하세요. "
                        "추천 장소명/주소/설명은 CONTEXT에 있는 내용을 우선 반영하고, "
                        "CONTEXT에 없는 내용을 단정하지 마세요.\n\n"
                        f"[CONTEXT INFORMATION]\n{context}"
                    ),
                }
            )
            print(f"[INFO] generate_response context_injected len={len(context)}")
        else:
            print("[WARN] generate_response context_injected=none")
        
        user_content = []
            
        # Location Context
        if location:
            user_content.append({"type": "text", "text": f"### Current User Location\n{location}\n\n"})

        # User Text
        user_content.append({"type": "text", "text": f"### User Question\n{user_input}"})

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
        content = response.choices[0].message.content
        print(f"[INFO] generate_response done output_len={len(content or '')}")
        return content
    except Exception as e:
        print(f"Error: {e}")
        return "죄송합니다. 오류가 발생했습니다."
