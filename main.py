from fastapi import Depends, FastAPI
from models.base import Base
from routes import auth, manage, online_songs, payments, playlist, premium, song_list, websocket
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager

from security.document_security import verify_docs
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("startup")
    yield
    print("shutdown")

app = FastAPI(lifespan=lifespan,
              docs_url=None,
              redoc_url=None,
              openapi_url=None
              )

_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://musicoindia-b08f2.web.app",
]
_cors_env = os.getenv("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)



@app.get("/docs", include_in_schema=False)
async def protected_docs(
    _: str = Depends(verify_docs)
):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Documentation"
    )


@app.get("/redoc", include_in_schema=False)
async def protected_redoc(
    _: str = Depends(verify_docs)
):
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="API Documentation"
    )

from fastapi.openapi.utils import get_openapi


@app.get("/openapi.json", include_in_schema=False)
async def protected_openapi(
    _: str = Depends(verify_docs)
):
    if app.openapi_schema:
        return app.openapi_schema

    app.openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    return app.openapi_schema

app.include_router(auth.router,prefix='/auth')
app.include_router(song_list.router,prefix='/local/songs')
app.include_router(playlist.router,prefix="/playlist")
app.include_router(online_songs.router,prefix="/api")
app.include_router(websocket.router,prefix="/sync")
app.include_router(payments.router,prefix="/payments")
app.include_router(premium.router,prefix="/subscribe")
app.include_router(manage.router,prefix="/manage")

Base.metadata.create_all(engine)




    
