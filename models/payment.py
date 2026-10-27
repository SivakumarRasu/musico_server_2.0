
from sqlalchemy import TEXT, TIMESTAMP, Column, Integer, String, func

from models.base import Base


class Payment(Base):
    __tablename__ ="payments"
    
    id=Column(TEXT,primary_key= True)
    razorpay_order_id = Column(String, unique=True)
    razorpay_payment_id = Column(String, unique=True)

    email = Column(String)
    username = Column(String)

    amount = Column(Integer)

    status = Column(String)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )
    