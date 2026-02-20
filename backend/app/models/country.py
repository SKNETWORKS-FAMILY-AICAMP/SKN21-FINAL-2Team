from sqlalchemy import Column, String
from app.models.orm import BaseModel

class Country(BaseModel):
    __tablename__ = "country"

    code = Column(String(10), primary_key=True, comment="ISO Country Code")
    name = Column(String(255), comment="Country Name")