from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.connection import get_db
from app.models.country import Country

router = APIRouter(prefix="/api/common", tags=["common"])

class CountryResponse(BaseModel):
    code: str
    name: str

    class Config:
        from_attributes = True

@router.get("/countries", response_model=List[CountryResponse])
def read_countries(db: Session = Depends(get_db)):
    return db.query(Country).all()
