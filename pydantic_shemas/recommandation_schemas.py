

from typing import List, Optional

from pydantic import BaseModel, Field


class GeminiTrack(BaseModel):
    song: str = Field(description="Name of the recommended song")
    artist: str = Field(description="Primary artist or composer name")
    movie: Optional[str] = Field(default=None, description="Movie or album name")

class GeminiRecommendationSchema(BaseModel):

    title:str
    recommendations: List[GeminiTrack]

class HistoryTrack(BaseModel):
    title:str = Field(description="Song title")
    artist:str = Field(description="Song primary artist")
    language:str = Field(description="Song language")
    
