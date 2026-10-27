from typing import Optional
from pydantic import BaseModel

class SyncEvent(BaseModel):
    type:str
    songUrl:Optional[str]=None
    position:int =0
    timestamp:int =0
    isPlaying:bool =False
    