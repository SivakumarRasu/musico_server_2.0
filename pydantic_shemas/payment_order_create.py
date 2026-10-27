from pydantic import BaseModel

class PaymentOrderCreate(BaseModel):
    class Config:
        from_attributes =True
    amount: int
    email: str
    username: str