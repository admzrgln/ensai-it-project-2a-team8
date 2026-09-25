from pydantic import BaseModel


class Movie(BaseModel):
    id: int
    original_title: str
    duration: int
    genre: str
