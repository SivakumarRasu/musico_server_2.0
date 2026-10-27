#database connection

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:root@localhost:5432/musicapp")

engine = create_engine(DATABASE_URL,echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

from models.app_version import AppVersion

Base.metadata.create_all(bind=engine)

def get_db():
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
