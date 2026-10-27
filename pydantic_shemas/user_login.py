from pydantic import BaseModel

class UserLogin(BaseModel):
    email:str
    password: str

class SingleUserLogin(BaseModel):
    email:str
    password: str
    device_id:str
