
import os
from dotenv import load_dotenv
from fastapi import HTTPException, Header
import jwt

load_dotenv()


def token_auth(auth_token=Header()):
    try:
        #get the access token from the headers
        if not auth_token:
             raise HTTPException(401,"No auth token, Access denied !")
        #decode the token 
        jwt_secret = os.getenv("JWT_SECRET", "password_key")
        verified_token=jwt.decode(auth_token,jwt_secret,['HS256'])
        if not verified_token:
            raise HTTPException(401,"Token Verification failed !,Authorization Denied")
        #get the id from token 
        uid = verified_token.get('id')
        device_id = verified_token.get('device_id')
        return {"uid":uid,"device_id":device_id,'token':auth_token}    
            # from db get user data with id
    except jwt.PyJWTError:
        raise HTTPException(401,"Token is not valid,Authorization failed")
    
