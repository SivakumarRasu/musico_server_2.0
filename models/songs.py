from sqlalchemy import TEXT, VARCHAR, Column
from models.base import Base

class Songs(Base):
     __tablename__="songs"
     id=Column(TEXT,primary_key=True)
     name=Column(VARCHAR(100))
     artist=Column(VARCHAR(100))
     thumbnail_url=Column(VARCHAR(255))
     song_url=Column(VARCHAR(255))
     color_code=Column(VARCHAR(6))
     mode=Column(VARCHAR(50))
     lyrics=Column(TEXT)