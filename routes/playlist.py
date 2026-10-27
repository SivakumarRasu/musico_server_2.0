
from typing import List
import os
import uuid
import cloudinary
from sqlalchemy import delete
from models import songs
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth_middleware import token_auth
from models.playlist import Playlist,playlist_song
from models.songs import Songs
from pydantic_shemas.playlist_create import PlaylistOut, SongOut
from pydantic_shemas.song_create import SongCreate



router=APIRouter(tags=['Playlist API'])
load_dotenv()
# Configuration       
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True
)

@router.post("/create",status_code=201)
def craete_playlists(thumbanil:UploadFile=File(...),color_code:str=Form(...),playlist_name:str=Form(...),db:Session=Depends(get_db),auth_dict= Depends(token_auth)):
    #upload Thumbnail
    playlist_id=str(uuid.uuid4())
    thumbanil_res=cloudinary.uploader.upload(thumbanil.file,resource_type='auto',folder=f'playlist/{playlist_id}')
    print(thumbanil_res['url'])
    
    new_playlist= Playlist(
        id=playlist_id,
        name=playlist_name,
        image_url=thumbanil_res['url'],
        color=color_code,
        user_id=auth_dict['uid']
    )
    
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    return new_playlist



@router.post("/add_song",status_code=201)
def add_song_to_playlist(
    song_id:str=Form(...),
    playlist_id: str=Form(...),
    db:Session=Depends(get_db),
    auth_dict=Depends(token_auth)
    ):
    playlist=db.query(Playlist).filter(Playlist.id==playlist_id).first()
    song=db.query(Songs).filter(Songs.id==song_id).first()
    if not playlist:
        raise HTTPException(status_code=404,detail="Playlist not found")
    if song in playlist.songs:
        return{'message':"Song is already in playlist"}
    playlist.songs.append(song)
    print(playlist.songs)
    db.commit()
    return {"message":"Song added successfully"}

@router.post("/add_new_song", status_code=201)
def add_new_song_to_playlist(
    id: str = Form(...),
    name: str = Form(...),
    artist: str = Form(...),
    thumbnail_url: str = Form(...),
    song_url: str = Form(...),
    color_code: str = Form(...),
    mode: str = Form(...),
    playlist_id: str = Form(...),
    lyrics:str =Form(...),
    db: Session = Depends(get_db),
    auth = Depends(token_auth)
):
    # 1️⃣ Get or create the song
    song = db.query(Songs).filter(Songs.id == id).first()
    if not song:
        song = Songs(
            id=id,
            name=name,
            artist=artist,
            thumbnail_url=thumbnail_url,
            song_url=song_url,
            color_code=color_code,
            mode=mode,
            lyrics = lyrics
        )
        db.add(song)
        db.commit()
        db.refresh(song)

    # 2️⃣ Fetch playlist
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # 3️⃣ Check if song already exists in the playlist
    if song in playlist.songs:
        return {"message": "Song already in playlist!"}

    # 4️⃣ Append and save
    playlist.songs.append(song)
    db.commit()
    db.refresh(playlist)
    return {"message": "Song added to playlist successfully!"}

    

@router.get("/get",status_code=200,response_model=List[PlaylistOut])
def get_playlists(db:Session=Depends(get_db),auth_dict=Depends(token_auth)):
    playlists=db.query(Playlist).filter(Playlist.user_id==auth_dict['uid']).all()
    return playlists;

@router.delete("/delete_playlist")
def delete_playlist(
    db: Session =Depends(get_db),
    playlist_id:str = Form(...),
    auth = Depends(token_auth)
):
    playlist = db.query(Playlist).filter(
    Playlist.id == playlist_id,
    Playlist.user_id == auth['uid']).first()
    if not playlist:
        raise HTTPException(status_code=404,detail="Playlist not found or Unauthorized access")
    db.delete(playlist)
    db.commit()
    return {"message":"Playlist deleted successfully"}
    

@router.delete("/delete_song_from_playlist")
def delete_fong_from_playlist(
    db: Session =Depends(get_db),
    playlist_id:str = Form(...),
    song_id: str = Form(...),
    auth = Depends(token_auth)
):
    playlist = db.query(Playlist).filter(
    Playlist.id == playlist_id,
    Playlist.user_id == auth['uid']).first()
    if not playlist:
        raise HTTPException(status_code=404,detail="Playlist not found or Unauthorized access")
    
    #delete statement for deleting a record from playlist_song table
    stmt = delete(playlist_song).where(
        playlist_song.c.playlist_id == playlist_id,
        playlist_song.c.song_id ==song_id,
    )
    res = db.execute(stmt)
    if res.rowcount==0:
        raise HTTPException(status_code=404,detail="Song not found in this playlist")
    db.commit()
    return {"message":"Song deleted from playlist successfully"}
