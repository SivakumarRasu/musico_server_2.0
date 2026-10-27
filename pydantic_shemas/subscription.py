from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubUpdatePayload(BaseModel):
    email: str
    is_premium: bool
    payment_added_date: datetime
    subscription_type: str
    subscription_expiry_date:datetime