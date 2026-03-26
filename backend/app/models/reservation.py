from sqlalchemy import Column, Integer, String, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.orm import BaseModel


class Reservation(BaseModel):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    date = Column(Date, nullable=True)
    image_path = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)

    user = relationship("User", back_populates="reservations")
