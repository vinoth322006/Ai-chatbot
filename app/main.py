
from typing import List, Any, Optional, Generator
from datetime import timedelta
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, UploadFile, File, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import ValidationError

# --- IMPORTS FROM SIMPLIFIED MODULES ---
from app import database as models
from app import schemas
from app.config import settings
from app import security
from app.services import AuthService, SessionService, DocumentService, ChatService, chat_service

# --- APP SETUP ---
app = FastAPI(title=settings.PROJECT_NAME)

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Serve index.html at root
@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')

# --- DEPENDENCIES ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(
    db: Session = Depends(models.get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = schemas.TokenData(username=username)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(models.User).filter(models.User.email == token_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# --- STARTUP EVENT ---
@app.on_event("startup")
def startup_event():
    models.init_db()

# --- ROUTES ---
api_router = APIRouter(prefix=settings.API_V1_STR)

# 1. AUTH
@api_router.post("/auth/register", response_model=schemas.UserResponse, status_code=201, tags=["auth"])
def register(
    *,
    db: Session = Depends(models.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    return AuthService.create_user(db=db, user_in=user_in)

@api_router.post("/auth/login", response_model=schemas.Token, tags=["auth"])
def login_access_token(
    db: Session = Depends(models.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.email, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

# 2. SESSIONS
@api_router.post("/sessions/", response_model=schemas.SessionResponse, status_code=201, tags=["sessions"])
def create_session(
    *,
    db: Session = Depends(models.get_db),
    session_in: schemas.SessionCreate,
    current_user: models.User = Depends(get_current_user),
) -> Any:
    return SessionService.create_session(db=db, session_in=session_in, user_id=current_user.id)

@api_router.get("/sessions/", response_model=List[schemas.SessionResponse], tags=["sessions"])
def read_sessions(
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    return SessionService.get_user_sessions(db=db, user_id=current_user.id)

@api_router.get("/sessions/{session_id}", response_model=schemas.SessionResponse, tags=["sessions"])
def read_session(
    session_id: UUID,
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    return SessionService.get_session(db=db, session_id=session_id, user_id=current_user.id)

@api_router.delete("/sessions/{session_id}", status_code=204, tags=["sessions"])
def delete_session(
    session_id: UUID,
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    SessionService.delete_session(db=db, session_id=session_id, user_id=current_user.id)

# 3. DOCUMENTS
@api_router.post("/documents/upload", response_model=schemas.DocumentResponse, tags=["documents"])
async def upload_document(
    *,
    db: Session = Depends(models.get_db),
    session_id: UUID = Query(..., description="ID of the chat session"),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    x_google_api_key: Optional[str] = Header(None, alias="x-google-api-key")
) -> Any:
    SessionService.get_session(db=db, session_id=session_id, user_id=current_user.id)
    # Passed API key to document service too (for embeddings)
    return await DocumentService.process_document(db=db, file=file, session_id=session_id, api_key=x_google_api_key)

@api_router.get("/documents/session/{session_id}", response_model=List[schemas.DocumentResponse], tags=["documents"])
def list_documents(
    session_id: UUID,
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    SessionService.get_session(db=db, session_id=session_id, user_id=current_user.id)
    return DocumentService.get_session_documents(db=db, session_id=session_id)

@api_router.delete("/documents/{document_id}", status_code=204, tags=["documents"])
def delete_document(
    document_id: UUID,
    session_id: UUID,
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    SessionService.get_session(db=db, session_id=session_id, user_id=current_user.id)
    DocumentService.delete_document(db=db, document_id=document_id, session_id=session_id)

# 4. CHAT
@api_router.post("/chat/", response_model=schemas.ChatResponse, tags=["chat"])
def chat(
    *,
    db: Session = Depends(models.get_db),
    chat_request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    x_google_api_key: Optional[str] = Header(None, alias="x-google-api-key")
) -> Any:
    SessionService.get_session(db=db, session_id=chat_request.session_id, user_id=current_user.id)
    return chat_service.process_message(db=db, chat_request=chat_request, api_key=x_google_api_key)

@api_router.get("/chat/session/{session_id}/history", response_model=schemas.ChatHistoryResponse, tags=["chat"])
def get_history(
    session_id: UUID,
    db: Session = Depends(models.get_db),
    current_user: models.User = Depends(get_current_user),
) -> Any:
    SessionService.get_session(db=db, session_id=session_id, user_id=current_user.id)
    history = chat_service.get_conversation_history(db=db, session_id=session_id)
    return schemas.ChatHistoryResponse(session_id=session_id, history=history)

# Register Router
app.include_router(api_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
