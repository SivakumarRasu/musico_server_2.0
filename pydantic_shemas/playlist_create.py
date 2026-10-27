from pydantic import BaseModel
from typing import List,Optional

from models.songs import Songs
from pydantic_shemas.song_create import SongCreate

class PlaylistCreate(BaseModel):
    name: str
    image_url: Optional[str]=None
    
class SongOut(BaseModel):
    id: str
    name: str
    artist: str
    thumbnail_url: str
    song_url: str
    color_code: str
    mode: str
    lyrics: Optional[str] = None

    class Config:
        from_attributes = True

class PlaylistOut(BaseModel):
    id: str
    name: str
    image_url: str
    user_id: str
    color:str
    songs: List[SongOut]  

    class Config:
        from_attributes = True
    