
import os
import random
import uuid
import bcrypt
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, File, HTTPException,APIRouter,UploadFile,Form
from pydantic import BaseModel

load_dotenv()

from database import get_db
from middleware.auth_middleware import token_auth
from models.user import User
from sqlalchemy.orm import Session

from pydantic_shemas.user_login import UserLogin,SingleUserLogin
import jwt

from services.mail_services import get_otp_template, trigger_background_email

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True
)

router = APIRouter(tags=['Authentication API'])

class PasswordChangeRequest(BaseModel):
    email: str
    new_password: str
    
@router.post('/signup', status_code=201)
def create_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    profile_pic: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user_db = db.query(User).filter(User.email == email).first()
    if user_db:
        raise HTTPException(400, "User with the same email already exists! Please Login.")

    profile = cloudinary.uploader.upload(profile_pic.file, resource_type='auto', folder=f'profiles/{email}')
    user_db = User(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        password=hashed_pw,
        profile_url=profile['url']
    )
    db.add(user_db)
    db.commit()
    return user_db


@router.post('/login')
def get_user(user:UserLogin,db:Session=Depends(get_db)):
    
    #checkin the user already exists with the email
    user_db = db.query(User).filter(User.email==user.email).first()
    
    if not user_db:
        raise HTTPException(400,"User with given email doesn't exist. Please sign up !")
    #checking the password matching or not
    is_match = bcrypt.checkpw(user.password.encode(),user_db.password)
    
    if not is_match:
        raise HTTPException(400,"Incorrect password !")
    
    jwt_secret = os.getenv("JWT_SECRET", "password_key")
    token = jwt.encode({'id':user_db.id}, jwt_secret)
    print(token)
    return {'token':token,'user':user_db}
    

@router.get('/')
def get_current_user(db: Session=Depends(get_db),user_dict:Session=Depends(token_auth)):
    
   id = user_dict['uid']
   token = user_dict['token']
   user_db = db.query(User).filter(User.id==id).first()
   if not user_db:
       raise HTTPException(404,"User not found")
   return user_db
    
    
@router.get("/send_forgot_password_otp")
def send_otp(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user_db = db.query(User).filter(User.email == email).first()
    if not user_db:
        raise HTTPException(404, "User not found")
        
    otp = str(random.randint(100000, 999999))
    
    trigger_background_email(
        background_tasks=background_tasks,
        to_email=email,
        subject="OTP for Musico password reset",
        html_content=get_otp_template(otp)
    )
    
    return {"otp": otp, "validity": 30}
    
@router.patch("/forget_password")
def change_password(request: PasswordChangeRequest, db: Session = Depends(get_db)):
    user_db = db.query(User).filter(User.email == request.email).first()
    if not user_db:
        raise HTTPException(404, "User not found")
        
    hashed_pw = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt())
    user_db.password = hashed_pw
    
    try:
        db.commit()
        return {"success": True, "message": "Password changed successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error updating password: {str(e)}")
    
    
@router.get("/user-exists-with-email")
def is_user_exists(email: str, db: Session = Depends(get_db)):
    clean_email = email.strip().lower()
    user_db = db.query(User).filter(User.email == clean_email).first()
    if not user_db:
        return {
            "email": email,
            "exists": False,
        }
    return {
        "exists": True,
        "message": f"User exists with email {user_db.email} !",
        "data": {
            "id": user_db.id,
            "email": user_db.email,
            "name": user_db.name,
            "profile_url": user_db.profile_url
        }
    }

@router.post("/secure/login")
def single_device_login(user:SingleUserLogin,db:Session = Depends(get_db)):
    user_db = db.query(User).filter(User.email==user.email).first()
    if not user_db:
        raise HTTPException(400,"User with given email doesn't exist. Please sign up !")
    is_match = bcrypt.checkpw(user.password.encode(),user_db.password)
    if not is_match:
        raise HTTPException(400,"Incorrect password !")
    user_db.active_device_id = user.device_id
    db.commit()
    db.refresh(user_db)
    jwt_secret = os.getenv("JWT_SECRET", "password_key")
    payload ={
        "id":user_db.id,
        "device_id":user.device_id
    }
    token = jwt.encode(payload, jwt_secret)
    print(token)
    return {'token':token,'user':user_db}

@router.get("/secure")
def single_get_current_user(db: Session=Depends(get_db),user_dict:Session=Depends(token_auth)):
    id = user_dict['uid']
    token_device_id = user_dict['device_id']
    user_db = db.query(User).filter(User.id==id).first()
    if not user_db:
       raise HTTPException(404,"User not found")

    if user_db.active_device_id != token_device_id:
        raise HTTPException(401,"Session expired. Your account logged in from another device.")
    
    return user_db
