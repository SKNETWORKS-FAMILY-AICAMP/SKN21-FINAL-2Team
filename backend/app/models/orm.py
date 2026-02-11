from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base
from app.models.enums import GenderType, RoleType

class BaseModel(Base):
    __abstract__ = True
