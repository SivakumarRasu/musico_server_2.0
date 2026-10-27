from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AdminPasswordUpdate(BaseModel):
    new_password: str = Field(min_length=6, description="New password for user, min 6 chars")


class AdminProfilePicUpdate(BaseModel):
    profile_url: str = Field(description="Direct URL to new profile image")


class AdminUserSummary(BaseModel):
    id: str
    name: str
    email: str
    profile_url: Optional[str] = None
    active_device_id: Optional[str] = None
    playlist_count: int = 0
    payment_count: int = 0
    has_paid: bool = False

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    total_count: int
    users: List[AdminUserSummary]


class AdminPlaylistSummary(BaseModel):
    id: str
    name: str
    image_url: Optional[str] = None
    color: Optional[str] = None
    user_id: str
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    song_count: int = 0

    class Config:
        from_attributes = True


class AdminPlaylistListResponse(BaseModel):
    total_count: int
    playlists: List[AdminPlaylistSummary]


class AdminPaymentSummary(BaseModel):
    id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    email: str
    username: Optional[str] = None
    amount: int
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminPaymentListResponse(BaseModel):
    total_count: int
    total_revenue_inr: float
    payments: List[AdminPaymentSummary]


class AdminDashboardStats(BaseModel):
    total_users: int
    total_playlists: int
    total_songs: int
    total_payments: int
    total_revenue_inr: float
    successful_payments_count: int


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: Optional[str] = "application/vnd.android.package-archive"
    folder: Optional[str] = "releases"


class PresignedUrlResponse(BaseModel):
    upload_url: str
    download_url: str
    s3_key: str
    bucket: str
    region: str
    expires_in: int


class AppVersionCreate(BaseModel):
    version_code: int = Field(gt=0, description="Integer version code e.g. 13")
    version_name: str = Field(min_length=1, description="String version name e.g. V2.4.2")
    download_url: Optional[str] = None
    s3_key: Optional[str] = None
    file_size: Optional[int] = None
    release_notes: Optional[str] = None
    is_force_update: bool = False
    is_active: bool = True


class AppVersionResponse(BaseModel):
    id: int
    version_code: int
    version_name: str
    download_url: Optional[str] = None
    s3_key: Optional[str] = None
    file_size: Optional[int] = None
    release_notes: Optional[str] = None
    is_force_update: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class S3ConfigStatus(BaseModel):
    is_configured: bool
    bucket: Optional[str] = None
    region: str
    custom_domain: Optional[str] = None
    has_access_key: bool
    has_secret_key: bool

