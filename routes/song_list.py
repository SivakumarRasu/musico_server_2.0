
from enum import auto
import os
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth_middleware import token_auth
from models.songs import Songs
from pydantic_shemas.song_create import SongCreate



import cloudinary
import cloudinary.uploader

load_dotenv()

# Configuration       
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True
)
router =APIRouter(tags =['Local API'])

@router.post('/upload',status_code=201)
def upload_song(song:UploadFile=File(...),thumbnail:UploadFile=File(...),
                artist:str=Form(...),song_name:str=Form(...),hex_code:str=Form(...),mode:str=Form(...),
                lyrics:str=Form(None),
                db: Session=Depends(get_db),
                auth_dict=Depends(token_auth)
                ):
    
    #Uploading Files
    song_id= str(uuid.uuid4())
    song_res =cloudinary.uploader.upload(song.file,resource_type='auto',folder=f'songs/{song_id}')
    print(song_res['url'])
    thumb_res= cloudinary.uploader.upload(thumbnail.file,resource_type='auto',folder=f'songs/{song_id}')
    
    print(thumb_res['url'])
    
    new_song = Songs(
        id=song_id,
        name=song_name,
     artist=artist,
     thumbnail_url=thumb_res['url'],
     song_url=song_res['url'],
     color_code=hex_code,
     mode=mode,
     lyrics=lyrics
    )
    
    db.add(new_song)
    db.commit()
    db.refresh(new_song)
    return new_song
    
@router.get('/get')
def get_songs(db: Session=Depends(get_db),auth_dict:Session=Depends(token_auth)):
    
    song_list = db.query(Songs).all()
    return song_list
    
    
