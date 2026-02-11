from sqlalchemy import Column, Integer, String, Text
from app.models.orm import BaseModel

class Prefer(BaseModel):
    __tablename__ = "prefers"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(255)) # actor, movie, etc
    type = Column(String(255))
    value = Column(String(255))
    image_path = Column(Text)