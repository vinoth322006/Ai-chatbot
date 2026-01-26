
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# --- AUTH ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    
    class Config:
        from_attributes = True

# --- SESSION ---
class SessionBase(BaseModel):
    name: Optional[str] = "Untitled Chat"

class SessionCreate(SessionBase):
    pass

class SessionResponse(SessionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    
    class Config:
        from_attributes = True

# --- DOCUMENT ---
class DocumentResponse(BaseModel):
    id: UUID
    session_id: UUID
    filename: str
    file_type: str
    chunks_count: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: UUID
    content: str
    
    class Config:
        from_attributes = True

# --- CHAT ---
class ChatRequest(BaseModel):
    session_id: UUID
    message: str

class ChatSourceDocument(BaseModel):
    id: UUID
    content: str

class ChatResponse(BaseModel):
    response: str
    source_documents: List[ChatSourceDocument]
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None

class ChatHistoryItem(BaseModel):
    message_order: int
    user_message: str
    bot_response: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    session_id: UUID
    history: List[ChatHistoryItem]
