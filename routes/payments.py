from fastapi import APIRouter, Depends
from requests import Session
from database import get_db
from middleware.auth_middleware import token_auth
from models.payment import Payment
from pydantic_shemas.payment_order_create import PaymentOrderCreate
from services.payment_services import client
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    tags=["Payment"]
)

@router.post("/create-order")
async def create_order(data: PaymentOrderCreate):
    order = client.order.create({
        "amount": data.amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    return {
        "success": True,
        "order_id": order["id"],
        "key": os.getenv("RAZORPAY_KEY_ID", "")
    }

@router.get("/get-all-payments")
def get_all_payments(db: Session = Depends(get_db)):
    payments = db.query(Payment).all()
    if not payments:
        return []
    return payments

@router.get("/get-user-payments")
def get_user_payments(email: str,auth = Depends(token_auth), db: Session = Depends(get_db)):
    return db.query(Payment).filter(Payment.email == email).all()
