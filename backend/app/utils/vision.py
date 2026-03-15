import mimetypes
import os
import base64
from typing import Optional
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.llm_factory import LLMFactory
from app.agents.prompts.prompts import IMAGE_TO_EMOTIONAL_PROMPT

load_dotenv()

async def describe_image(image_data: str) -> Optional[str]:
    """
    Extracts emotional and descriptive text from an image using GPT-4o-mini.
    image_data: http/https URL, local absolute file path, or data:image base64 URL.
    """
    try:
        if image_data.startswith("http"):
            from app.scripts.preprocess_data import download_image
            from io import BytesIO
            img = download_image(image_data)
            if img:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{image_base64}"
            else:
                return None
        elif image_data.startswith("data:image"):
            image_url = image_data
        elif os.path.exists(image_data):
            # 로컬 절대 파일 path
            mime_type, _ = mimetypes.guess_type(image_data)
            with open(image_data, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            image_url = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"
        else:
            image_url = f"data:image/jpeg;base64,{image_data}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", IMAGE_TO_EMOTIONAL_PROMPT),
            ("human", [
                {"type": "image_url", "image_url": {"url": image_url}}
            ])
        ])

        llm = LLMFactory.get_llm()
        response = await llm.ainvoke(prompt)
        description = response.content.strip()
        print(f"[INFO] describe_image output: {description}")
        return description
    except Exception as e:
        print(f"[ERROR] describe_image failed: {e}")
        return None
