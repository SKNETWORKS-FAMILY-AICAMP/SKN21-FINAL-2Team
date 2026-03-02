from pydantic import BaseModel


class CountryBase(BaseModel):
    code: str
    name: str


class CountryResponse(CountryBase):
    class Config:
        from_attributes = True
