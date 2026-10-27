


from sqlalchemy import TEXT, VARCHAR, Column, LargeBinary
from sqlalchemy.orm import relationship
from models.base import Base


class User(Base):
    __tablename__='users'
    
    id=Column(TEXT,primary_key= True)
    name =Column(VARCHAR(100))
    email= Column(VARCHAR(100))
    password =Column(LargeBinary)
    profile_url = Column(TEXT)
    active_device_id = Column(TEXT,nullable =True)
    playlists=relationship("Playlist",back_populates="owner")
