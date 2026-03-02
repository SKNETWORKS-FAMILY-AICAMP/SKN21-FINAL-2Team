from sqlalchemy import Column, Integer, String, Text
from app.models.orm import BaseModel


class HotPlace(BaseModel):
    __tablename__ = "hot_places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=True)
    adress = Column(Text, nullable=True)
    feature = Column(Text, nullable=True)
    tag1 = Column(Text, nullable=True)
    tag2 = Column(Text, nullable=True)
    image_path = Column(String(255), nullable=True)
