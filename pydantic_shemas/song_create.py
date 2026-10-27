from pydantic import BaseModel
from typing import Optional

class SongCreate(BaseModel):
    song:str
    artist:str
    thumbnail_url:str
    song_url: str
    color_code:str
    mode:str
    lyrics: Optional[str] = None