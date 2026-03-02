from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.models.orm import BaseModel


class Reservation(BaseModel):
    __tablename__ = "reservation_list"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    date = Column(Date, nullable=True)
    image_path = Column(String(255), nullable=True)

    user = relationship("User", back_populates="reservations")
