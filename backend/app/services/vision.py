import os
import base64
from typing import Optional
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.utils.llm_factory import LLMFactory
from app.services.prompts import IMAGE_TO_EMOTIONAL_PROMPT

load_dotenv()

def describe_image(image_data: str) -> Optional[str]:
    """
    Extracts emotional and descriptive text from an image using GPT-4o-mini.
    image_data: Base64 string or URL.
    """
    try:
        if image_data.startswith("http"):
            from app.scripts.preprocess_data import download_image
            import base64
            from io import BytesIO
            img = download_image(image_data)
            if img:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{image_base64}"
            else:
                return None
        else:
            image_url = image_data if image_data.startswith("data:image") else f"data:image/jpeg;base64,{image_data}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", IMAGE_TO_EMOTIONAL_PROMPT),
            ("human", [
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ])

        response = LLMFactory.get_llm().invoke(prompt)
        description = response.content.strip()
        print(f"[INFO] describe_image output: {description}")
        return description
    except Exception as e:
        print(f"[ERROR] describe_image failed: {e}")
        return None
