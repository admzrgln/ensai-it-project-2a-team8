from pydantic import BaseModel
from typing import Optional


class Movie(BaseModel):
    id: Optional[int] = None 
    title: str
    duration: int
    genre: str
    external_id: str
    poster_url: str
