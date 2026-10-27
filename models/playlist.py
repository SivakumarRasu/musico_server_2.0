
from sqlalchemy import TEXT, Column, ForeignKey,Table
from sqlalchemy.orm import relationship
from models.base import Base

playlist_song=Table(
    'playlist_song',Base.metadata,
        Column('playlist_id',ForeignKey('playlists.id'),primary_key=True),
        Column('song_id',ForeignKey('songs.id',ondelete='CASCADE'),primary_key=True)
                    )

class Playlist(Base):
    __tablename__="playlists"
    
    id=Column(TEXT,primary_key=True)
    name =Column(TEXT)
    image_url=Column(TEXT)
    color=Column(TEXT)
    user_id=Column(TEXT,ForeignKey("users.id"))
    
    
    owner=relationship("User",back_populates="playlists")
    songs=relationship("Songs",secondary=playlist_song,backref="playlists")
