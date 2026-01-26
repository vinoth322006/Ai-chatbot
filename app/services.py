
from typing import List, Tuple, Any, Optional
from uuid import UUID
from datetime import datetime
import io

from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from fastapi import UploadFile, HTTPException

# Langchain Imports for Google & HuggingFace
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# App imports
from app.config import settings
from app import schemas
from app import database as models
from app import security

# --- VECTOR SERVICE (LOCAL HUGGINGFACE) ---
class VectorService:
    def __init__(self):
        # Initialize local embeddings (CPU based, no API key needed)
        print("Initializing Local Embeddings (all-MiniLM-L6-v2)...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def embed_text(self, text: str, api_key: str = None) -> List[float]:
        # api_key is ignored for local embeddings
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, texts: List[str], api_key: str = None) -> List[List[float]]:
        # api_key is ignored for local embeddings
        return self.embeddings.embed_documents(texts)

# Global instance
vector_service = VectorService()

# --- AUTH SERVICE ---
class AuthService:
    @staticmethod
    def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
        user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )
        
        user_data = user_in.model_dump(exclude={"password"})
        user_data["password_hash"] = security.get_password_hash(user_in.password)
        
        db_user = models.User(**user_data)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

# --- SESSION SERVICE ---
class SessionService:
    @staticmethod
    def create_session(db: Session, session_in: schemas.SessionCreate, user_id: UUID) -> models.Session:
        db_session = models.Session(**session_in.model_dump(), user_id=user_id)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def get_user_sessions(db: Session, user_id: UUID) -> List[models.Session]:
        return db.query(models.Session).filter(
            models.Session.user_id == user_id,
            models.Session.is_archived == False
        ).order_by(models.Session.created_at.desc()).all()

    @staticmethod
    def get_session(db: Session, session_id: UUID, user_id: UUID) -> Optional[models.Session]:
        session = db.query(models.Session).filter(
            models.Session.id == session_id,
            models.Session.user_id == user_id,
            models.Session.is_archived == False
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    @staticmethod
    def delete_session(db: Session, session_id: UUID, user_id: UUID) -> None:
        session = db.query(models.Session).filter(
            models.Session.id == session_id,
            models.Session.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Soft delete
        session.is_archived = True
        db.commit()

# --- DOCUMENT SERVICE ---
class DocumentService:
    @staticmethod
    async def process_document(
        db: Session,
        file: UploadFile,
        session_id: UUID,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        api_key: str = None
    ) -> models.Document:
        # 1. Read file content
        content = await file.read()
        file_size = len(content)
        
        # 2. Extract text based on file type
        text = ""
        if file.filename.endswith(".pdf"):
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                text += page. extract_text() + "\n"
        elif file.filename.endswith(".txt"):
            text = content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Only .pdf and .txt allowed.")
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty document or could not extract text")

        # 3. Create Document record
        db_document = models.Document(
            session_id=session_id,
            filename=file.filename,
            file_type=file.filename.split(".")[-1],
            original_size_bytes=file_size,
        )
        db.add(db_document)
        db.flush() # Get ID
        
        # 4. Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        chunks_text = text_splitter.split_text(text)
        db_document.chunks_count = len(chunks_text)
        
        # 5. Generate embeddings and store chunks
        try:
            embeddings = vector_service.embed_documents(chunks_text, api_key=api_key)
        except Exception as e:
            db.delete(db_document)
            db.commit()
            raise HTTPException(status_code=400, detail=f"Embedding Error: {str(e)}")
        
        for i, (chunk_text, embedding) in enumerate(zip(chunks_text, embeddings)):
            db_chunk = models.DocumentChunk(
                document_id=db_document.id,
                chunk_index=i,
                content=chunk_text,
                token_count=len(chunk_text) // 4
            )
            db.add(db_chunk)
            db.flush()
            
            db_embedding = models.DocumentEmbedding(
                chunk_id=db_chunk.id,
                embedding=embedding
            )
            db.add(db_embedding)
            
        db.commit()
        db.refresh(db_document)
        return db_document

    @staticmethod
    def get_session_documents(db: Session, session_id: UUID) -> List[models.Document]:
        return db.query(models.Document).filter(models.Document.session_id == session_id).all()

    @staticmethod
    def delete_document(db: Session, document_id: UUID, session_id: UUID) -> None:
        document = db.query(models.Document).filter(
            models.Document.id == document_id,
            models.Document.session_id == session_id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        db.delete(document)
        db.commit()

# --- CHAT SERVICE (GOOGLE GEMINI) ---
class ChatService:
    def __init__(self):
        self.default_api_key = settings.GOOGLE_API_KEY
    
    def _get_llm(self, api_key: str = None):
        key = api_key or self.default_api_key
        return ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=key,
            temperature=0.7,
            convert_system_message_to_human=True
        )

    def retrieve_context(self, db: Session, query: str, session_id: UUID, k: int = 4, api_key: str = None) -> List[Tuple[models.DocumentChunk, float]]:
        # 1. Embed query
        try:
            query_vector = vector_service.embed_text(query, api_key=api_key)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Embedding Error: {str(e)}")
        
        # 2. Vector search (PGVector)
        # Using Local Embeddings (384 dims)
        stmt = (
            select(models.DocumentChunk)
            .join(models.DocumentEmbedding)
            .join(models.Document)
            .filter(models.Document.session_id == session_id)
            .order_by(models.DocumentEmbedding.embedding.cosine_distance(query_vector))
            .limit(k)
        )
        chunks = db.scalars(stmt).all()
        return chunks

    def get_history(self, db: Session, session_id: UUID, limit: int = 10) -> List[models.Conversation]:
        return db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.message_order.desc()).limit(limit).all()

    def process_message(self, db: Session, chat_request: schemas.ChatRequest, api_key: str = None) -> schemas.ChatResponse:
        # 1. Retrieve Context
        relevant_chunks = self.retrieve_context(db, chat_request.message, chat_request.session_id, api_key=api_key)
        
        context_text = "\n\n".join([f"Source ({c.document.filename}): {c.content}" for c in relevant_chunks])
        
        # 2. Retrieve History
        history = self.get_history(db, chat_request.session_id)
        history.sort(key=lambda x: x.message_order)
        
        # 3. Construct Prompt
        messages = [
            SystemMessage(content=f"You are a helpful AI assistant. Use the following context to answer the user's question. If the answer is not in the context, say so.\n\nContext:\n{context_text}"),
        ]
        
        for turn in history:
            messages.append(HumanMessage(content=turn.user_message))
            messages.append(AIMessage(content=turn.bot_response))
            
        messages.append(HumanMessage(content=chat_request.message))
        
        # 4. Generate Response
        try:
            llm = self._get_llm(api_key)
            response = llm.invoke(messages)
        except Exception as e:
            return schemas.ChatResponse(
                response=f"Error calling Google Gemini API: {str(e)}",
                source_documents=[],
                tokens_used=0
            )
        
        # 5. Store Conversation
        last_msg = db.query(models.Conversation).filter(models.Conversation.session_id == chat_request.session_id).order_by(models.Conversation.message_order.desc()).first()
        new_order = (last_msg.message_order + 1) if last_msg else 0
        
        chunk_ids = [c.id for c in relevant_chunks]
        
        new_conv = models.Conversation(
            session_id=chat_request.session_id,
            message_order=new_order,
            user_message=chat_request.message,
            bot_response=response.content,
            context_chunks=chunk_ids,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            processing_time_ms=0
        )
        db.add(new_conv)
        db.commit()
        
        # 6. Return Response
        source_docs = [
            schemas.ChatSourceDocument(id=c.id, content=c.content) 
            for c in relevant_chunks
        ]
        
        return schemas.ChatResponse(
            response=response.content,
            source_documents=source_docs,
            tokens_used=new_conv.tokens_used
        )

    @staticmethod
    def get_conversation_history(db: Session, session_id: UUID) -> List[models.Conversation]:
         return db.query(models.Conversation).filter(
            models.Conversation.session_id == session_id
        ).order_by(models.Conversation.created_at.asc()).all()

chat_service = ChatService()
