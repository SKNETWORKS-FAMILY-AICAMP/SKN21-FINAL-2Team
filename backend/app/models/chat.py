from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    image: str | None = None
    location: str | None = None

class ChatResponse(BaseModel):
    reply: str