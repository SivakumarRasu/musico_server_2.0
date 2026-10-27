from datetime import datetime
from sqlalchemy import TEXT, VARCHAR, Boolean, Column, DateTime, Integer, BigInteger
from models.base import Base


class AppVersion(Base):
    __tablename__ = 'app_versions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_code = Column(Integer, nullable=False, index=True)
    version_name = Column(VARCHAR(50), nullable=False)
    download_url = Column(TEXT, nullable=True)
    s3_key = Column(TEXT, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    release_notes = Column(TEXT, nullable=True)
    is_force_update = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
