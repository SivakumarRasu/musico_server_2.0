from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from fastapi.responses import HTMLResponse
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

security = HTTPBasic(
    scheme_name="Musico API Login",
    description="Musico API doumentation login"
)

DOCS_USERNAME = os.getenv("DOCS_USERNAME", "admin@musico")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "")


def verify_docs(credentials: HTTPBasicCredentials = Depends(security)):
    username_correct = secrets.compare_digest(
        credentials.username,
        DOCS_USERNAME
    )

    password_correct = secrets.compare_digest(
        credentials.password,
        DOCS_PASSWORD
    )

    if not (username_correct and password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username