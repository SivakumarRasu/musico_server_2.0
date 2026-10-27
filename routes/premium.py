from sqlalchemy.exc import IntegrityError
import os
import uuid
import hmac
import hashlib
import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Form, UploadFile, File, Request, status
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

load_dotenv()
from database import get_db
from models.user import User
from models.payment import Payment
from services.mail_services import get_welcome_template, trigger_background_email

router = APIRouter(
    tags=["Subscription API"],
)
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    email: str = Form(...),
    username: str = Form(None),
    password: str = Form(None),
    profile_photo: UploadFile = File(None),
    razorpay_payment_id: str = Form(...),
    razorpay_order_id: str = Form(...),
    razorpay_signature: str = Form(None),
    amount: int = Form(...),
    status: str = Form("captured"),
    db: Session = Depends(get_db),
    bgtasks: BackgroundTasks = None
):
    signature = request.headers.get("X-Razorpay-Signature") or razorpay_signature

    if not signature:
        raise HTTPException(
            status_code=400, 
            detail="Missing mandatory Razorpay signature verification payload."
        )
    razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    verified = False
    
    if razorpay_secret:
        expected_pay_sig = hmac.new(
            key=razorpay_secret.encode('utf-8'),
            msg=f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(expected_pay_sig, signature):
            verified = True
            
    # 2. Fallback: Try verifying as webhook signature (using RAZORPAY_WEBHOOK_SECRET)
    if not verified:
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
        if webhook_secret:
            try:
                body = await request.body()
                expected_web_sig = hmac.new(
                    key=webhook_secret.encode('utf-8'),
                    msg=body,
                    digestmod=hashlib.sha256
                ).hexdigest()
                
                if hmac.compare_digest(expected_web_sig, signature):
                    verified = True
            except RuntimeError:
                pass

    if not verified:
        raise HTTPException(
            status_code=400, 
            detail="Signature verification mismatch. Unauthorized payment event rejected."
        )

    existing_payment = db.query(Payment).filter(
        Payment.razorpay_payment_id == razorpay_payment_id
    ).first()
    
    if existing_payment:
        return {"success": True, "message": "Payment Already exists in Database !"}

    new_payment = Payment(
        id=str(uuid.uuid4()),  
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        email=email.strip().lower(),
        username=username or "Premium User",
        amount=amount // 100,    
        status=status.lower().strip() 
    )

    try:
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Transaction log collision: This order or payment ID has already been recorded."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while writing payment data: {str(e)}"
        )

    # 3. Create a new user in the standard Users table
    clean_email = email.strip().lower()
    user_db = db.query(User).filter(User.email == clean_email).first()

    if not user_db:
        if not username or not password or not profile_photo:
            raise HTTPException(
                status_code=400,
                detail="User registration requires username, password, and profile photo."
            )

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            profile = cloudinary.uploader.upload(
                profile_photo.file, 
                resource_type='auto', 
                folder=f'profiles/{clean_email}'
            )
            profile_url = profile.get('url')
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to upload profile picture to cloud storage.")
            
        user_db = User(
            id=str(uuid.uuid4()),
            name=username,
            email=clean_email,
            password=hashed_pw,           
            profile_url=profile_url
        )
        
        try:
            db.add(user_db)
            db.commit()
            db.refresh(user_db)
            if bgtasks:
                trigger_background_email(
                    background_tasks=bgtasks,
                    to_email=user_db.email,
                    subject="Account Created Successfully",
                    html_content=get_welcome_template(
                        name=user_db.name,
                        email=user_db.email,
                        profile_url=user_db.profile_url
                    )
                )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database transaction failure: {str(e)}")

    return {
        "success": True,
        "message": "Payment recorded and user created successfully!",
        "payment": {
            "id": new_payment.id,
            "razorpay_payment_id": new_payment.razorpay_payment_id,
            "amount": new_payment.amount,
            "status": new_payment.status
        },
        "user": {
            "id": user_db.id,
            "name": user_db.name,
            "email": user_db.email,
            "profile_url": user_db.profile_url
        }
    }
