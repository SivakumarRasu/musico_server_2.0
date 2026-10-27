import logging
import os
import secrets
from typing import List, Optional
import bcrypt
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models.app_version import AppVersion
from models.payment import Payment
from models.playlist import Playlist, playlist_song
from models.songs import Songs
from models.user import User
from pydantic_shemas.manage_schemas import (
    AdminDashboardStats,
    AdminPasswordUpdate,
    AdminPaymentListResponse,
    AdminPaymentSummary,
    AdminPlaylistListResponse,
    AdminPlaylistSummary,
    AdminUserListResponse,
    AdminUserSummary,
    AppVersionCreate,
    AppVersionResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    S3ConfigStatus,
)
from services.s3_service import S3Service

from pydantic_shemas.playlist_create import PlaylistOut
from security.document_security import DOCS_PASSWORD, DOCS_USERNAME

load_dotenv()

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["Management Portal API"])

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True,
)

security = HTTPBasic(
    scheme_name="Admin Management Portal Auth",
    auto_error=False,
)


def verify_admin(
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
):
    """
    Verify admin access via either HTTP Basic Auth or X-Admin-Key header.
    """
    # 1. Check X-Admin-Key header
    if x_admin_key and secrets.compare_digest(x_admin_key, DOCS_PASSWORD):
        return DOCS_USERNAME

    # 2. Check HTTP Basic Auth credentials
    if credentials:
        user_match = secrets.compare_digest(credentials.username, DOCS_USERNAME)
        pass_match = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
        if user_match and pass_match:
            return credentials.username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Admin access required",
        headers={"WWW-Authenticate": "Basic"},
    )


# ==========================================
# 1. DASHBOARD & STATS OVERVIEW
# ==========================================

@router.get("/stats", response_model=AdminDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Retrieve high-level overview metrics for the management portal."""
    total_users = db.query(User).count()
    total_playlists = db.query(Playlist).count()
    total_songs = db.query(Songs).count()
    total_payments = db.query(Payment).count()

    successful_payments = db.query(Payment).filter(Payment.status == "captured").all()
    successful_payments_count = len(successful_payments)
    total_revenue_inr = sum(p.amount for p in successful_payments) / 100.0 if successful_payments else 0.0

    return AdminDashboardStats(
        total_users=total_users,
        total_playlists=total_playlists,
        total_songs=total_songs,
        total_payments=total_payments,
        total_revenue_inr=total_revenue_inr,
        successful_payments_count=successful_payments_count,
    )


# ==========================================
# 2. USER MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List registered users with search, pagination, playlist counts, and payment status."""
    query = db.query(User)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))

    total_count = query.count()
    users = query.order_by(User.name.asc()).offset(skip).limit(limit).all()

    # Pre-fetch payment emails for quick lookup
    captured_emails = set(
        p[0] for p in db.query(Payment.email).filter(Payment.status == "captured").all() if p[0]
    )
    payment_counts = dict(
        db.query(Payment.email, func.count(Payment.id)).group_by(Payment.email).all()
    )
    playlist_counts = dict(
        db.query(Playlist.user_id, func.count(Playlist.id)).group_by(Playlist.user_id).all()
    )

    user_summaries = []
    for u in users:
        u_email = (u.email or "").strip().lower()
        user_summaries.append(
            AdminUserSummary(
                id=u.id,
                name=u.name,
                email=u.email,
                profile_url=u.profile_url,
                active_device_id=u.active_device_id,
                playlist_count=playlist_counts.get(u.id, 0),
                payment_count=payment_counts.get(u_email, 0),
                has_paid=u_email in captured_emails,
            )
        )

    return AdminUserListResponse(total_count=total_count, users=user_summaries)


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Retrieve detailed profile of a user, including their playlists and payments."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_playlists = db.query(Playlist).filter(Playlist.user_id == user_id).all()
    user_payments = db.query(Payment).filter(Payment.email == user.email).all()

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "profile_url": user.profile_url,
        "active_device_id": user.active_device_id,
        "playlists": [
            {
                "id": p.id,
                "name": p.name,
                "image_url": p.image_url,
                "color": p.color,
                "song_count": len(p.songs) if p.songs else 0,
            }
            for p in user_playlists
        ],
        "payments": [
            {
                "id": p.id,
                "razorpay_order_id": p.razorpay_order_id,
                "razorpay_payment_id": p.razorpay_payment_id,
                "amount": p.amount,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in user_payments
        ],
    }


@router.patch("/users/{user_id}/password")
def update_user_password(
    user_id: str,
    payload: AdminPasswordUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Update a user's password directly from the management portal."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_pw = bcrypt.hashpw(payload.new_password.encode("utf-8"), bcrypt.gensalt())
    user.password = hashed_pw
    # Reset active device session so user must re-authenticate with new password
    user.active_device_id = None

    try:
        db.commit()
        return {
            "success": True,
            "message": f"Password for user '{user.email}' updated successfully.",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating password for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/users/{user_id}/profile-pic")
def update_user_profile_pic(
    user_id: str,
    profile_pic: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Update a user's profile picture using either an uploaded file (Cloudinary)
    or a direct image URL string.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_profile_url = None

    # Option 1: File upload to Cloudinary
    if profile_pic and profile_pic.filename:
        try:
            res = cloudinary.uploader.upload(
                profile_pic.file,
                resource_type="auto",
                folder=f"profiles/{user.email}",
            )
            new_profile_url = res.get("url")
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

    # Option 2: Direct image URL string
    elif image_url and image_url.strip():
        new_profile_url = image_url.strip()

    else:
        raise HTTPException(
            status_code=400,
            detail="Either a profile_pic file or image_url must be provided.",
        )

    user.profile_url = new_profile_url
    try:
        db.commit()
        return {
            "success": True,
            "message": "Profile picture updated successfully.",
            "profile_url": user.profile_url,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Database error updating profile url: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/users/{user_id}")
def delete_user_safely(
    user_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Safely delete a user and all associated dependencies to prevent PostgreSQL
    foreign key constraint violations.
    
    Deletion Sequence:
    1. Fetch user's playlists.
    2. Remove all song associations from playlist_song junction table for those playlists.
    3. Delete all playlists owned by the user.
    4. Delete the user record atomically.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_email = user.email
    user_playlists = db.query(Playlist).filter(Playlist.user_id == user_id).all()
    playlist_ids = [p.id for p in user_playlists]

    try:
        # Step 1: Clean up playlist_song junction rows
        if playlist_ids:
            db.execute(
                playlist_song.delete().where(playlist_song.c.playlist_id.in_(playlist_ids))
            )

        # Step 2: Delete user's playlists
        if playlist_ids:
            db.query(Playlist).filter(Playlist.user_id == user_id).delete(synchronize_session=False)

        # Step 3: Delete the user
        db.delete(user)

        # Step 4: Commit atomic transaction
        db.commit()

        logger.info(
            f"Admin safely deleted user '{user_email}' (ID: {user_id}) along with {len(playlist_ids)} playlists."
        )
        return {
            "success": True,
            "message": f"User '{user_email}' and {len(playlist_ids)} associated playlists safely deleted.",
            "deleted_playlists_count": len(playlist_ids),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Safe user deletion failed for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to safely delete user: {str(e)}")


# ==========================================
# 3. PLAYLIST MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/playlists", response_model=AdminPlaylistListResponse)
def list_all_playlists(
    search: Optional[str] = Query(None, description="Search by playlist name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List all created playlists across all users with owner details and song count."""
    query = db.query(Playlist)

    if search:
        query = query.filter(Playlist.name.ilike(f"%{search.strip()}%"))

    total_count = query.count()
    playlists = query.order_by(Playlist.name.asc()).offset(skip).limit(limit).all()

    # Pre-fetch owners for performance
    user_ids = list(set(p.user_id for p in playlists if p.user_id))
    users_map = {
        u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    results = []
    for p in playlists:
        owner = users_map.get(p.user_id)
        results.append(
            AdminPlaylistSummary(
                id=p.id,
                name=p.name,
                image_url=p.image_url,
                color=p.color,
                user_id=p.user_id or "",
                owner_name=owner.name if owner else "Unknown",
                owner_email=owner.email if owner else "Unknown",
                song_count=len(p.songs) if p.songs else 0,
            )
        )

    return AdminPlaylistListResponse(total_count=total_count, playlists=results)


@router.get("/users/{user_id}/playlists", response_model=List[PlaylistOut])
def list_playlists_by_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List all playlists created by a particular user with full song details."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    playlists = db.query(Playlist).filter(Playlist.user_id == user_id).all()
    return playlists


@router.get("/playlists/{playlist_id}", response_model=PlaylistOut)
def get_playlist_detail(
    playlist_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Get single playlist details including songs array."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.delete("/playlists/{playlist_id}")
def delete_playlist_directly(
    playlist_id: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Directly delete any playlist as admin without ownership check.
    Safely removes references from playlist_song junction table.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    playlist_name = playlist.name

    try:
        # Step 1: Remove song associations in junction table
        db.execute(
            playlist_song.delete().where(playlist_song.c.playlist_id == playlist_id)
        )

        # Step 2: Delete playlist
        db.delete(playlist)
        db.commit()

        logger.info(f"Admin directly deleted playlist '{playlist_name}' (ID: {playlist_id}).")
        return {
            "success": True,
            "message": f"Playlist '{playlist_name}' deleted successfully.",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error directly deleting playlist {playlist_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error deleting playlist: {str(e)}")


# ==========================================
# 4. PAYMENT AUDITING & MANAGEMENT
# ==========================================

@router.get("/payments", response_model=AdminPaymentListResponse)
def list_all_payments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by payment status (e.g. captured, failed)"),
    search: Optional[str] = Query(None, description="Search by email, username, order ID, or payment ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List all payment transactions with status filtering, search, and gross revenue sum."""
    query = db.query(Payment)

    if status_filter:
        query = query.filter(Payment.status.ilike(status_filter.strip()))

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Payment.email.ilike(term),
                Payment.username.ilike(term),
                Payment.razorpay_order_id.ilike(term),
                Payment.razorpay_payment_id.ilike(term),
            )
        )

    total_count = query.count()
    payments = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()

    # Calculate total captured revenue in INR
    captured_sum_query = db.query(func.sum(Payment.amount)).filter(Payment.status == "captured")
    if search:
        term = f"%{search.strip()}%"
        captured_sum_query = captured_sum_query.filter(
            or_(
                Payment.email.ilike(term),
                Payment.username.ilike(term),
                Payment.razorpay_order_id.ilike(term),
                Payment.razorpay_payment_id.ilike(term),
            )
        )
    total_amount_paise = captured_sum_query.scalar() or 0
    total_revenue_inr = float(total_amount_paise) / 100.0

    payment_summaries = [
        AdminPaymentSummary(
            id=p.id,
            razorpay_order_id=p.razorpay_order_id,
            razorpay_payment_id=p.razorpay_payment_id,
            email=p.email or "",
            username=p.username,
            amount=p.amount or 0,
            status=p.status or "unknown",
            created_at=p.created_at,
        )
        for p in payments
    ]

    return AdminPaymentListResponse(
        total_count=total_count,
        total_revenue_inr=total_revenue_inr,
        payments=payment_summaries,
    )


@router.get("/payments/user/{email}", response_model=List[AdminPaymentSummary])
def get_user_payments_by_email(
    email: str,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List all payment records associated with a specific user email."""
    payments = (
        db.query(Payment)
        .filter(Payment.email.ilike(email.strip()))
        .order_by(Payment.created_at.desc())
        .all()
    )
    return [
        AdminPaymentSummary(
            id=p.id,
            razorpay_order_id=p.razorpay_order_id,
            razorpay_payment_id=p.razorpay_payment_id,
            email=p.email or "",
            username=p.username,
            amount=p.amount or 0,
            status=p.status or "unknown",
            created_at=p.created_at,
        )
        for p in payments
    ]


# ==============================================================================
# APP VERSION & AWS S3 RELEASES MANAGEMENT
# ==============================================================================

s3_service = S3Service()


@router.get("/version/s3-status", response_model=S3ConfigStatus)
def get_s3_config_status(admin: str = Depends(verify_admin)):
    """Check whether AWS S3 credentials and bucket are configured in the environment."""
    return s3_service.get_s3_status()


@router.get("/version", response_model=Optional[AppVersionResponse])
def get_current_app_version(
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Get the currently active client release version."""
    active_version = (
        db.query(AppVersion)
        .filter(AppVersion.is_active == True)
        .order_by(AppVersion.version_code.desc(), AppVersion.id.desc())
        .first()
    )
    if not active_version:
        return AppVersionResponse(
            id=0,
            version_code=12,
            version_name="V2.4.1",
            download_url=None,
            s3_key=None,
            file_size=None,
            release_notes="Initial baseline release",
            is_force_update=False,
            is_active=True,
            created_at=None,
            updated_at=None,
        )
    return active_version


@router.get("/version/history", response_model=List[AppVersionResponse])
def get_version_history(
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """List all previous releases ordered by version code descending."""
    return (
        db.query(AppVersion)
        .order_by(AppVersion.version_code.desc(), AppVersion.id.desc())
        .all()
    )


@router.post("/version/presigned-url", response_model=PresignedUrlResponse)
def get_s3_presigned_upload_url(
    req: PresignedUrlRequest,
    admin: str = Depends(verify_admin),
):
    """Generate a pre-signed AWS S3 PUT URL for uploading release files directly to S3."""
    try:
        res = s3_service.generate_presigned_upload_url(
            filename=req.filename,
            content_type=req.content_type or "application/vnd.android.package-archive",
            folder=req.folder or "releases",
        )
        return PresignedUrlResponse(**res)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"S3 presigned URL generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 Presigned URL error: {str(e)}",
        )


@router.post("/version", response_model=AppVersionResponse)
def publish_app_version(
    payload: AppVersionCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Publish a new app version. Deactivates previous versions and sets this as active.
    """
    if payload.is_active:
        db.query(AppVersion).filter(AppVersion.is_active == True).update({"is_active": False})

    new_version = AppVersion(
        version_code=payload.version_code,
        version_name=payload.version_name.strip(),
        download_url=payload.download_url.strip() if payload.download_url else None,
        s3_key=payload.s3_key.strip() if payload.s3_key else None,
        file_size=payload.file_size,
        release_notes=payload.release_notes.strip() if payload.release_notes else None,
        is_force_update=payload.is_force_update,
        is_active=payload.is_active,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    logger.info(
        f"Admin published new AppVersion: Code={new_version.version_code}, Name={new_version.version_name}"
    )
    return new_version


@router.post("/version/{version_id}/activate", response_model=AppVersionResponse)
def activate_version(
    version_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Rollback or switch active release to a specific version."""
    target = db.query(AppVersion).filter(AppVersion.id == version_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")

    db.query(AppVersion).update({"is_active": False})
    target.is_active = True
    db.commit()
    db.refresh(target)
    return target


@router.post("/version/upload-fallback")
async def upload_version_fallback(
    file: UploadFile = File(...),
    admin: str = Depends(verify_admin),
):
    """
    Server-side fallback upload to S3 if browser direct S3 CORS is not configured.
    """
    try:
        content = await file.read()
        res = s3_service.upload_file_direct(
            file_bytes=content,
            filename=file.filename,
            content_type=file.content_type or "application/vnd.android.package-archive",
            folder="releases",
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Fallback S3 upload error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

