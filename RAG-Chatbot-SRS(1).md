# Software Requirements Specification (SRS)
## RAG Chatbot with Document Context Backend

**Version:** 1.0  
**Date:** January 24, 2026  
**Status:** Final  
**Author:** Development Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Data Requirements](#data-requirements)
6. [API Specifications](#api-specifications)
7. [Technology Stack](#technology-stack)
8. [System Architecture](#system-architecture)
9. [Database Schema](#database-schema)
10. [Security Requirements](#security-requirements)
11. [Performance Requirements](#performance-requirements)
12. [Deployment & DevOps](#deployment--devops)
13. [Quality Assurance](#quality-assurance)
14. [Risk & Mitigation](#risk--mitigation)

---

## 1. Executive Summary

### 1.1 Project Overview

The RAG Chatbot Backend is a production-grade REST API service that enables users to:
- Upload documents (PDF, TXT)
- Interact with an AI chatbot powered by GPT-4
- Get context-aware responses using Retrieval Augmented Generation (RAG)
- Maintain per-user conversation history with session isolation

### 1.2 Project Scope

**Included:**
- User authentication and authorization (JWT)
- Document upload and processing pipeline
- Vector embedding generation and storage
- RAG-powered chat interface (API only)
- Conversation history management
- Session-based document isolation
- Docker containerization
- PostgreSQL + pgvector integration

**Not Included:**
- Frontend UI (web or mobile)
- User-facing analytics dashboard
- Advanced admin panel
- Third-party LLM provider integrations (focus on OpenAI)
- Fine-tuning capabilities

### 1.3 Stakeholders

- **End Users:** Individual users who want to upload documents and ask questions
- **System Administrator:** Deploys, monitors, maintains the application
- **Evaluators:** Assess code quality, architecture, implementation completeness
- **Future Maintainers:** Support and extend the system

### 1.4 Success Criteria

- All functional requirements fully implemented
- All endpoints tested and working
- Database schema properly optimized
- Code well-documented with descriptive comments
- README with clear setup and execution instructions
- Docker deployment verified working
- RAG pipeline delivering relevant, context-aware responses
- Authentication and authorization working flawlessly

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────┐
│              HTTP Client                        │
│     (Testing tools, future frontend)            │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS/REST
                   ▼
┌──────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11)                   │
│  ┌────────────────────────────────────────────┐  │
│  │ Authentication Layer (JWT)                 │  │
│  │ Route Handlers (Auth, Chat, Docs, Sessions)  │
│  │ Middleware (CORS, Error Handling)          │  │
│  └────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │ Service Layer                              │  │
│  │ - RAG Service (LangChain chain)            │  │
│  │ - LLM Service (OpenAI API calls)           │  │
│  │ - Document Service (PDF/TXT processing)    │  │
│  │ - Embedding Service (Vector generation)    │  │
│  │ - Auth Service (JWT, password hashing)     │  │
│  │ - Conversation Service (History mgmt)      │  │
│  └────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │ Data Access Layer (SQLAlchemy ORM)         │  │
│  │ - Models (User, Session, Document, etc)    │  │
│  │ - Database connection pooling               │  │
│  └────────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────────┘
        SQL ▲      │ SQL ▼
             │      │
             │      ▼
┌──────────────────────────────────────────────────┐
│  PostgreSQL (14+) with pgvector                  │
│  ┌────────────────────────────────────────────┐  │
│  │ Tables:                                    │  │
│  │ - users, sessions, documents               │  │
│  │ - document_chunks, document_embeddings     │  │
│  │ - conversations                            │  │
│  │ - Vector indices (IVFFlat)                 │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
        ▲
        │ External APIs
        │
┌──────────────────────────────────────────────────┐
│  OpenAI API (GPT-4, Embeddings)                  │
└──────────────────────────────────────────────────┘
```

### 2.2 System Actors

1. **Unauthenticated User**
   - Can register and login only
   - No access to chat or document features

2. **Authenticated User**
   - Can create chat sessions
   - Can upload documents
   - Can send messages and receive RAG responses
   - Can view conversation history
   - Can only access their own data

3. **System Administrator**
   - Deploys application
   - Configures environment variables
   - Monitors logs and performance
   - Manages database backups

### 2.3 System Constraints

- Maximum file upload size: 25 MB
- Maximum message length: 4000 characters
- JWT token expiration: 24 hours
- Rate limiting: 100 requests per hour per user (configurable)
- Document chunk size: 1000 characters
- Retrieved context chunks: 4 (configurable)
- Supported document formats: PDF, TXT only
- Single LLM provider initially: OpenAI

---

## 3. Functional Requirements

### 3.1 Authentication & User Management (FR-AUTH)

#### FR-AUTH-1: User Registration
**Requirement:** User should be able to register with email, username, password, and optional full name.

**Description:**
- User provides: email, username (3-100 chars), password (8+ chars), optional full name
- System validates email format and uniqueness
- System validates username uniqueness
- System hashes password using bcrypt
- System creates user record in database
- System returns JWT access token and user profile

**Acceptance Criteria:**
- Valid registration creates user and returns token
- Duplicate email rejected with 400 error
- Duplicate username rejected with 400 error
- Weak passwords (< 8 chars) rejected
- Invalid email format rejected
- All user data persisted correctly in database

**API Endpoint:** `POST /api/auth/register`

---

#### FR-AUTH-2: User Login
**Requirement:** User should be able to login with email and password.

**Description:**
- User provides email and password
- System looks up user by email
- System verifies password against stored hash
- System generates JWT token valid for 24 hours
- System returns token and user profile
- Failed attempts logged for security

**Acceptance Criteria:**
- Valid credentials return token
- Invalid email returns 401 Unauthorized
- Invalid password returns 401 Unauthorized
- Token expires after 24 hours
- Token can be verified by backend

**API Endpoint:** `POST /api/auth/login`

---

#### FR-AUTH-3: User Profile
**Requirement:** Authenticated user should retrieve their profile.

**Description:**
- User sends request with valid JWT token
- System verifies token validity
- System returns user profile information

**Acceptance Criteria:**
- Valid token returns user data
- Invalid token returns 401 Unauthorized
- Expired token returns 401 Unauthorized

**API Endpoint:** `GET /api/auth/profile` (optional enhancement)

---

### 3.2 Session Management (FR-SESSION)

#### FR-SESSION-1: Create Chat Session
**Requirement:** User should create new chat sessions to organize conversations.

**Description:**
- User creates new session with optional name
- System generates UUID for session
- System associates session with user
- System persists session metadata

**Acceptance Criteria:**
- Session created with auto-generated UUID
- Session name defaults to "Untitled Chat"
- Session timestamp recorded
- Only authenticated user can access their sessions
- Multiple sessions per user supported

**API Endpoint:** `POST /api/sessions/`

---

#### FR-SESSION-2: List User Sessions
**Requirement:** User should view all their sessions.

**Description:**
- User requests list of sessions
- System retrieves all active (non-archived) sessions for user
- System returns sessions ordered by creation date (newest first)
- System includes session metadata (name, created_at, document count)

**Acceptance Criteria:**
- Only user's own sessions returned
- Archived sessions excluded
- Sorted by creation date (descending)
- Response includes session count

**API Endpoint:** `GET /api/sessions/`

---

#### FR-SESSION-3: Get Session Details
**Requirement:** User should view specific session details.

**Description:**
- User provides session ID
- System verifies session ownership
- System returns complete session information

**Acceptance Criteria:**
- Returns session details if owned by user
- Returns 404 if session not found
- Returns 403 if session not owned by user

**API Endpoint:** `GET /api/sessions/{session_id}`

---

#### FR-SESSION-4: Delete/Archive Session
**Requirement:** User should archive sessions.

**Description:**
- User marks session for deletion
- System soft-deletes (archives) session
- Associated documents and conversations archived with session

**Acceptance Criteria:**
- Session marked as archived
- Data not physically deleted (preserves audit trail)
- Archived sessions excluded from list view
- Cannot unarchive (one-way operation)

**API Endpoint:** `DELETE /api/sessions/{session_id}`

---

### 3.3 Document Management (FR-DOC)

#### FR-DOC-1: Upload Document
**Requirement:** User should upload PDF or TXT documents for RAG context.

**Description:**
- User uploads file (PDF or TXT)
- System validates file type and size (max 25 MB)
- System extracts text from document
- System chunks text into overlapping segments (1000 chars, 200 char overlap)
- System generates embeddings for each chunk
- System stores chunks and embeddings in database
- System returns upload confirmation

**Acceptance Criteria:**
- Only PDF and TXT files accepted
- Files > 25 MB rejected
- Invalid files rejected
- Text extracted correctly from PDFs
- Chunks created with specified overlap
- Each chunk < 1500 tokens
- Embeddings generated and stored
- Document metadata persisted

**API Endpoint:** `POST /api/documents/upload?session_id={id}`

---

#### FR-DOC-2: List Session Documents
**Requirement:** User should view all documents uploaded to a session.

**Description:**
- User provides session ID
- System verifies session ownership
- System returns all documents in session with metadata

**Acceptance Criteria:**
- Only user's documents returned
- Includes filename, file type, upload date, chunk count
- Sorted by upload date (newest first)
- Returns 404 if session not found

**API Endpoint:** `GET /api/documents/session/{session_id}`

---

#### FR-DOC-3: Delete Document
**Requirement:** User should delete documents from sessions.

**Description:**
- User provides document ID
- System verifies document ownership (via session)
- System deletes document, chunks, and embeddings
- System removes document from vector store

**Acceptance Criteria:**
- Document deleted if owned by user
- Associated chunks deleted
- Associated embeddings deleted
- Returns 404 if not found
- Returns 403 if not owned

**API Endpoint:** `DELETE /api/documents/{document_id}`

---

### 3.4 Chat & RAG Pipeline (FR-CHAT)

#### FR-CHAT-1: Send Chat Message
**Requirement:** User should send messages and receive RAG-powered responses.

**Description:**
- User sends message to session
- System verifies session ownership
- System embeds user message
- System retrieves top-4 relevant document chunks (vector similarity)
- System retrieves conversation history (last 10 exchanges)
- System constructs prompt with context + history
- System calls OpenAI GPT-4 API
- System stores message pair in database
- System returns response with source documents

**Acceptance Criteria:**
- Message processed within 30 seconds (SLA)
- Response generated using RAG context
- Source documents returned with response
- Conversation stored for history
- Tokens tracked for usage monitoring
- Processing time recorded
- Empty messages rejected
- Message length capped at 4000 chars

**API Endpoint:** `POST /api/chat/`

---

#### FR-CHAT-2: Get Conversation History
**Requirement:** User should retrieve conversation history for a session.

**Description:**
- User requests conversation history for session
- System verifies session ownership
- System returns all conversation pairs (user message + bot response)
- System returns in chronological order

**Acceptance Criteria:**
- Returns all conversations in session
- Ordered by creation time (oldest first)
- Includes metadata (timestamp, tokens used, processing time)
- Returns 404 if session not found
- Returns 403 if not owned

**API Endpoint:** `GET /api/chat/session/{session_id}/history`

---

#### FR-CHAT-3: Clear Conversation History
**Requirement:** User should clear conversation history (optional enhancement).

**Description:**
- User requests to clear history for session
- System deletes all conversations for session
- Documents remain untouched

**Acceptance Criteria:**
- All conversations deleted
- Documents preserved
- Session metadata untouched
- Operation logged for audit

**API Endpoint:** `DELETE /api/chat/session/{session_id}/history` (optional)

---

### 3.5 Error Handling (FR-ERROR)

#### FR-ERROR-1: Comprehensive Error Responses
**Requirement:** All errors should be returned with clear, actionable messages.

**Description:**
- System catches exceptions at handler level
- System returns standardized error response with:
  - HTTP status code (400, 401, 403, 404, 500, etc.)
  - Error message (human-readable)
  - Error code (for programmatic handling)
  - Timestamp

**Acceptance Criteria:**
- All endpoints return proper HTTP status codes
- Error messages are clear and actionable
- No stack traces exposed in production
- 401 for auth failures
- 403 for permission failures
- 404 for not found
- 400 for validation errors
- 500 for server errors
- Errors logged server-side

**Standard Error Response:**
```json
{
  "error": "Unauthorized",
  "detail": "Invalid or expired token",
  "status_code": 401,
  "timestamp": "2026-01-24T13:30:00Z"
}
```

---

## 4. Non-Functional Requirements

### 4.1 Performance (NFR-PERF)

#### NFR-PERF-1: Response Time
- Chat response: < 30 seconds (including LLM latency)
- Document upload: < 60 seconds (including embedding generation)
- Session list: < 1 second
- Chat history: < 5 seconds
- P95 latency: within 2x of P50

#### NFR-PERF-2: Throughput
- Backend supports minimum 100 concurrent users
- Minimum 10 requests/second sustained
- Database query optimization with proper indexing
- Connection pooling enabled (min 5, max 20 connections)

#### NFR-PERF-3: Scalability
- Horizontal scaling possible via Docker
- Stateless service design
- Database connection pooling
- No in-memory session state

### 4.2 Reliability (NFR-REL)

#### NFR-REL-1: Availability
- Target 99% uptime
- Graceful degradation on external API failures
- Database failover support (PostgreSQL replication)
- Health check endpoint `/health`

#### NFR-REL-2: Data Consistency
- ACID compliance for all database operations
- Transaction isolation level: READ_COMMITTED
- No race conditions in chat history
- Document chunks never partially stored

#### NFR-REL-3: Error Recovery
- Automatic retry logic for transient failures (max 3 retries)
- Exponential backoff for API calls
- Graceful timeout handling
- Connection timeout: 30 seconds
- Request timeout: 120 seconds

### 4.3 Security (NFR-SEC)

#### NFR-SEC-1: Authentication
- JWT tokens with HS256 algorithm
- Tokens expire after 24 hours
- Password hashed with bcrypt (rounds: 12)
- No password logging
- Secure token transmission only (HTTPS required in production)

#### NFR-SEC-2: Authorization
- User can only access their own sessions/documents
- Database queries filtered by user_id
- No privilege escalation possible
- Role-based access control (RBAC) framework prepared for future

#### NFR-SEC-3: Data Protection
- HTTPS/TLS required in production
- API keys stored in environment variables (never in code)
- Database credentials in environment variables
- File uploads scanned for malicious content (future)
- SQL injection prevention via parameterized queries (SQLAlchemy ORM)
- XSS prevention via proper serialization

#### NFR-SEC-4: Audit & Logging
- All authentication attempts logged
- All data access logged (optional: detailed)
- Logs stored separately from application
- Sensitive data (passwords, tokens) never logged
- Audit trail maintained for compliance

### 4.4 Usability (NFR-USE)

#### NFR-USE-1: API Design
- RESTful API design principles followed
- Consistent error response format
- Clear, descriptive endpoint names
- API versioning ready (v1/ prefix)
- Comprehensive API documentation

#### NFR-USE-2: Documentation
- README with complete setup instructions
- API documentation with examples
- Code comments for complex logic
- Architecture diagrams included
- Troubleshooting guide provided

### 4.5 Maintainability (NFR-MAINT)

#### NFR-MAINT-1: Code Quality
- Code organized by concern (routes, services, models)
- Single responsibility principle applied
- DRY (Don't Repeat Yourself) principle
- Linting with flake8, formatting with black
- Type hints for all functions (Python 3.11)

#### NFR-MAINT-2: Testing
- Unit test coverage > 70%
- Integration tests for API endpoints
- E2E test suite for critical flows
- Performance tests for RAG pipeline
- All tests automated in CI/CD

#### NFR-MAINT-3: Monitoring
- Logging to stdout/stderr (container-friendly)
- Structured logging with JSON format
- Application metrics (response time, errors)
- Database monitoring (connection pool, query slow logs)
- Alert thresholds configured

---

## 5. Data Requirements

### 5.1 Data Dictionary

#### User Data
```
id: UUID (PK)
email: VARCHAR(255) UNIQUE NOT NULL
username: VARCHAR(100) UNIQUE NOT NULL
password_hash: VARCHAR(255) NOT NULL
full_name: VARCHAR(255) NULLABLE
is_active: BOOLEAN (default: true)
created_at: TIMESTAMP (default: NOW())
updated_at: TIMESTAMP (default: NOW())
```

#### Session Data
```
id: UUID (PK)
user_id: UUID (FK -> users.id)
name: VARCHAR(255) (default: "Untitled Chat")
created_at: TIMESTAMP (default: NOW())
updated_at: TIMESTAMP (default: NOW())
is_archived: BOOLEAN (default: false)
```

#### Document Data
```
id: UUID (PK)
session_id: UUID (FK -> sessions.id)
filename: VARCHAR(255) NOT NULL
file_type: VARCHAR(10) NOT NULL (pdf, txt)
original_size_bytes: INT
chunks_count: INT
uploaded_at: TIMESTAMP (default: NOW())
```

#### Document Chunk Data
```
id: UUID (PK)
document_id: UUID (FK -> documents.id)
chunk_index: INT NOT NULL
content: TEXT NOT NULL
token_count: INT
created_at: TIMESTAMP (default: NOW())
```

#### Document Embedding Data
```
id: UUID (PK)
chunk_id: UUID (FK -> document_chunks.id)
embedding: vector(1536) (OpenAI embedding vector)
created_at: TIMESTAMP (default: NOW())
```

#### Conversation Data
```
id: UUID (PK)
session_id: UUID (FK -> sessions.id)
message_order: INT NOT NULL
user_message: TEXT NOT NULL
bot_response: TEXT NOT NULL
context_chunks: TEXT[] (array of chunk IDs used)
tokens_used: INT
processing_time_ms: INT
created_at: TIMESTAMP (default: NOW())
```

### 5.2 Data Storage

- **Database:** PostgreSQL 14+
- **Vector Extension:** pgvector for embeddings
- **Storage Capacity:** Designed for 10GB+ datasets
- **Retention:** All data retained indefinitely (user deletion archives data)
- **Backup:** Daily automated backups (restore within 24 hours)
- **Recovery Time Objective (RTO):** 1 hour
- **Recovery Point Objective (RPO):** 1 day

### 5.3 Data Security

- Encryption at rest: PostgreSQL native encryption (future)
- Encryption in transit: HTTPS/TLS
- Access control: Database user permissions, application-level authorization
- PII: Minimal - only email required
- Compliance: GDPR-ready (user deletion support to be added)

---

## 6. API Specifications

### 6.1 Base Configuration

**Base URL:** `http://localhost:8000/api` (development)  
**Protocol:** HTTP/REST  
**Content-Type:** application/json  
**Authentication:** Bearer Token (JWT)  
**Response Format:** JSON

### 6.2 Standard Response Format

**Success Response (2xx):**
```json
{
  "data": { /* endpoint-specific data */ },
  "message": "Success message",
  "status_code": 200
}
```

**Error Response (4xx, 5xx):**
```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "status_code": 400,
  "timestamp": "2026-01-24T13:30:00Z"
}
```

### 6.3 Authentication Endpoints

#### POST /api/auth/register

**Request:**
```json
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "SecurePass123",
  "full_name": "Test User"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "is_active": true
  }
}
```

**Error Responses:**
- 400: Invalid email format, username exists, weak password
- 409: Email already registered

---

#### POST /api/auth/login

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "is_active": true
  }
}
```

**Error Responses:**
- 401: Invalid email or password
- 403: User account inactive

---

### 6.4 Session Endpoints

#### POST /api/sessions/

**Headers:**
```
Authorization: Bearer {token}
```

**Request:**
```json
{
  "name": "My Chat Session"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Chat Session",
  "created_at": "2026-01-24T13:30:00Z",
  "updated_at": "2026-01-24T13:30:00Z",
  "is_archived": false
}
```

---

#### GET /api/sessions/

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Chat Session",
    "created_at": "2026-01-24T13:30:00Z",
    "updated_at": "2026-01-24T13:30:00Z",
    "is_archived": false
  }
]
```

---

#### GET /api/sessions/{session_id}

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Chat Session",
  "created_at": "2026-01-24T13:30:00Z",
  "updated_at": "2026-01-24T13:30:00Z",
  "is_archived": false
}
```

**Error Responses:**
- 404: Session not found
- 403: Session not owned by user

---

#### DELETE /api/sessions/{session_id}

**Headers:**
```
Authorization: Bearer {token}
```

**Response (204 No Content)**

---

### 6.5 Document Endpoints

#### POST /api/documents/upload

**Headers:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Query Parameters:**
```
session_id: UUID (required)
```

**Request:**
```
file: File (PDF or TXT, max 25 MB)
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "research.pdf",
  "chunks_created": 45,
  "session_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses:**
- 400: Unsupported file type, file too large
- 404: Session not found
- 413: Payload too large

---

#### GET /api/documents/session/{session_id}

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "research.pdf",
    "file_type": "pdf",
    "chunks_count": 45,
    "uploaded_at": "2026-01-24T13:30:00Z"
  }
]
```

---

#### DELETE /api/documents/{document_id}

**Headers:**
```
Authorization: Bearer {token}
```

**Response (204 No Content)**

---

### 6.6 Chat Endpoints

#### POST /api/chat/

**Headers:**
```
Authorization: Bearer {token}
```

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "What are the main topics in the uploaded document?"
}
```

**Response (200 OK):**
```json
{
  "response": "Based on the document, the main topics are...",
  "source_documents": [
    {
      "id": "chunk-id-1",
      "content": "Relevant chunk from document..."
    },
    {
      "id": "chunk-id-2",
      "content": "Another relevant chunk..."
    }
  ],
  "tokens_used": 450,
  "processing_time_ms": 2150
}
```

**Error Responses:**
- 400: Empty message, message too long
- 404: Session not found
- 500: LLM API failure (with graceful error message)

---

#### GET /api/chat/session/{session_id}/history

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "history": [
    {
      "message_order": 0,
      "user_message": "Hello, who are you?",
      "bot_response": "I'm an AI assistant...",
      "tokens_used": 150,
      "processing_time_ms": 1200,
      "created_at": "2026-01-24T13:30:00Z"
    }
  ]
}
```

---

### 6.7 Health Check

#### GET /health

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2026-01-24T13:30:00Z",
  "version": "1.0.0"
}
```

---

## 7. Technology Stack

### 7.1 Core Technologies

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| **Language** | Python | 3.11+ | LangChain maturity, type safety, fast development |
| **Web Framework** | FastAPI | 0.104+ | Async support, automatic API docs, type validation |
| **ASGI Server** | Uvicorn | 0.24+ | High performance, production-ready |
| **ORM** | SQLAlchemy | 2.0+ | Powerful, industry-standard, type-safe |
| **Database** | PostgreSQL | 14+ | Reliability, pgvector extension, ACID compliance |
| **Vector Extension** | pgvector | 0.2+ | Native vector support, efficient similarity search |
| **LLM Framework** | LangChain | 0.1+ | RAG implementation, prompt management, memory |
| **LLM Provider** | OpenAI | API | GPT-4 capability, reliable embeddings API |
| **Embeddings Model** | text-embedding-3-small | Latest | Fast, accurate, 1536-dimensional vectors |
| **Password Hashing** | bcrypt | Via passlib | Industry standard, time-tested security |
| **JWT** | python-jose | 3.3+ | Flexible, lightweight token handling |
| **PDF Processing** | PyPDF | 3.17+ | Pure Python, no external dependencies |
| **Text Splitting** | LangChain | Built-in | Optimized for RAG, handles overlap correctly |

### 7.2 Development & DevOps

| Tool | Purpose | Justification |
|------|---------|---------------|
| **Docker** | Containerization | Reproducible environments, easy deployment |
| **docker-compose** | Local orchestration | One-command development setup |
| **Git** | Version control | Distributed, industry standard |
| **Black** | Code formatting | Consistent style enforcement |
| **flake8** | Linting | Code quality checks |
| **pytest** | Testing | Comprehensive testing framework |
| **Pre-commit** | Git hooks | Prevent bad commits |

### 7.3 Dependencies

**Core (`requirements.txt`):**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
langchain==0.1.0
langchain-openai==0.0.6
langchain-community==0.0.10
openai==1.3.0
pypdf==3.17.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
email-validator==2.1.0
pgvector==0.2.4
python-cors==4.0.0
```

**Development:**
```
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.12.0
flake8==6.1.0
mypy==1.7.1
ipython==8.17.2
```

---

## 8. System Architecture

### 8.1 Layered Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                 │
│  (Routes: auth, chat, documents, sessions)                  │
├─────────────────────────────────────────────────────────────┤
│                  Middleware Layer                            │
│  (Auth, CORS, Error Handling, Logging)                      │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ RAG Service  │ │ LLM Service  │ │Auth Service  │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │Doc Service   │ │Embedding Svc │ │Conversation  │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                   Data Access Layer                          │
│  (SQLAlchemy ORM, Database Models)                          │
├─────────────────────────────────────────────────────────────┤
│              External & Database Layer                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ PostgreSQL   │ │ OpenAI API   │ │ pgvector     │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Component Responsibilities

**API Layer:**
- Route handling
- Request validation
- Response formatting
- HTTP status codes

**Middleware Layer:**
- JWT token verification
- CORS handling
- Exception catching
- Request/response logging

**Service Layer:**
- Business logic implementation
- Orchestration of components
- External API calls
- Error handling

**Data Access Layer:**
- Database queries
- Transaction management
- Model persistence
- Query optimization

### 8.3 Data Flow: Chat Request

```
1. Client sends POST /api/chat/ with message
   ↓
2. FastAPI validates request
   ↓
3. Middleware extracts and verifies JWT token
   ↓
4. Route handler verifies session ownership
   ↓
5. RAG Service processes query:
   a. Embed user message (OpenAI API)
   b. Search PostgreSQL for relevant chunks
   c. Retrieve conversation history
   d. Format prompt with context
   ↓
6. LLM Service calls GPT-4 API
   ↓
7. Conversation Service stores message pair in database
   ↓
8. Response returned to client with source documents
```

### 8.4 RAG Pipeline Architecture

```
User Message
    ↓
[Embedding Service] → OpenAI embeddings API
    ↓
Query Vector (1536-dim)
    ↓
[Vector Search] → PostgreSQL + pgvector
    ↓
Top 4 Chunks (cosine similarity)
    ↓
[LLM Service]
    │
    ├─ System Prompt (with document context)
    ├─ Conversation History (last 10 messages)
    ├─ User Message
    │
    └→ OpenAI GPT-4 API
       ↓
   Generated Response
       ↓
[Conversation Service] → Store in PostgreSQL
       ↓
Return to Client (response + source documents)
```

---

## 9. Database Schema

### 9.1 Entity Relationship Diagram

```
┌─────────────┐
│   Users     │
├─────────────┤
│ id (PK)     │
│ email       │──┐
│ username    │  │ 1:N
│ password_h  │  │
│ full_name   │  │
│ is_active   │  │
│ created_at  │  │
└─────────────┘  │
                 │
                 ↓
         ┌───────────────┐
         │  Sessions     │
         ├───────────────┤
         │ id (PK)       │
         │ user_id (FK)  │
         │ name          │──┐
         │ created_at    │  │ 1:N
         │ is_archived   │  │
         └───────────────┘  │
                            ├─→ ┌──────────────┐
                            │   │  Documents   │
                            │   ├──────────────┤
                            │   │ id (PK)      │
                            │   │ session(FK)  │
                            │   │ filename     │──┐
                            │   │ file_type    │  │ 1:N
                            │   │ chunks_count │  │
                            │   │ uploaded_at  │  │
                            │   └──────────────┘  │
                            │                     ↓
                            │        ┌────────────────────────┐
                            │        │ Document_Chunks        │
                            │        ├────────────────────────┤
                            │        │ id (PK)                │
                            │        │ document_id (FK)       │
                            │        │ chunk_index            │
                            │        │ content                │──┐
                            │        │ token_count            │  │ 1:1
                            │        │ created_at             │  │
                            │        └────────────────────────┘  │
                            │                                     ↓
                            │            ┌─────────────────────────┐
                            │            │ Document_Embeddings     │
                            │            ├─────────────────────────┤
                            │            │ id (PK)                 │
                            │            │ chunk_id (FK)           │
                            │            │ embedding (vector1536)  │
                            │            │ created_at              │
                            │            └─────────────────────────┘
                            │
                            └──→ ┌──────────────────┐
                                 │ Conversations    │
                                 ├──────────────────┤
                                 │ id (PK)          │
                                 │ session_id (FK)  │
                                 │ message_order    │
                                 │ user_message     │
                                 │ bot_response     │
                                 │ context_chunks[] │
                                 │ tokens_used      │
                                 │ created_at       │
                                 └──────────────────┘
```

### 9.2 Indexing Strategy

```sql
-- Users table
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Sessions table
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);

-- Documents table
CREATE INDEX idx_documents_session ON documents(session_id);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at);

-- Document_Chunks table
CREATE INDEX idx_chunks_document ON document_chunks(document_id);

-- Document_Embeddings table (CRITICAL for performance)
CREATE INDEX idx_embeddings_chunk ON document_embeddings(chunk_id);
CREATE INDEX idx_embeddings_vector ON document_embeddings 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Conversations table
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_order ON conversations(session_id, message_order);
```

### 9.3 Data Volume Estimates

| Table | Rows | Growth/Month | Disk Space |
|-------|------|--------------|-----------|
| users | 1000 | 100 | 100 KB |
| sessions | 5000 | 1000 | 500 KB |
| documents | 10000 | 2000 | 2 MB |
| document_chunks | 500000 | 100000 | 100 MB |
| document_embeddings | 500000 | 100000 | 2 GB (vectors) |
| conversations | 100000 | 20000 | 50 MB |
| **Total** | | | **2.1 GB** |

---

## 10. Security Requirements

### 10.1 Authentication & Authorization

#### Authentication Strategy
- JWT (JSON Web Tokens) with HS256 algorithm
- Token issued on successful login
- Token stored in Authorization header: `Bearer {token}`
- Token expiration: 24 hours
- Token refresh: Not implemented in MVP

#### Password Security
- Minimum 8 characters
- Hashing: bcrypt with 12 rounds
- No password validation rules (future enhancement)
- Password reset: Not implemented in MVP

#### Authorization Logic
- Every protected endpoint checks JWT validity
- User can only access their own data
- Database queries filtered by `user_id`
- No privilege escalation possible

### 10.2 API Security

#### CORS (Cross-Origin Resource Sharing)
- Whitelist trusted origins
- Allow credentials in requests
- Configure allowed methods (GET, POST, DELETE)
- Configure allowed headers

#### Input Validation
- Email format validation
- File size validation (max 25 MB)
- Message length validation (max 4000 chars)
- Username length validation (3-100 chars)
- No script injection via validation

#### Rate Limiting
- 100 requests per hour per user (configurable)
- Per-endpoint rate limits (optional enhancement)
- Graceful rejection with 429 Too Many Requests

### 10.3 Data Security

#### Database Security
- Credentials in environment variables
- No hardcoded database URLs
- Parameterized queries (SQLAlchemy ORM prevents SQL injection)
- Connection encryption (SSL optional)
- Regular backups

#### API Keys
- OpenAI API key in environment variables
- Never logged or exposed
- Secrets manager support (future)
- API key rotation (future)

#### PII Handling
- Only email as PII
- No tracking of user behavior
- No third-party data sharing
- Data retention: indefinite until user deletion
- User deletion: soft-delete (archive) in MVP

### 10.4 Logging & Monitoring

#### What Gets Logged
- Authentication attempts (success/failure)
- API endpoint access (non-sensitive data only)
- Errors and exceptions
- Data access patterns (optional)

#### What Should NOT Be Logged
- Passwords
- API keys
- JWT tokens
- User messages (optional: log metadata only)
- Personal information

#### Log Storage
- Stdout/stderr (Docker-friendly)
- Structured logging (JSON format)
- Timestamp and severity level
- Log rotation (if file-based)

### 10.5 Infrastructure Security

#### HTTPS/TLS
- Mandatory in production
- Self-signed certificates in development
- Certificate validation enabled
- HTTP redirect to HTTPS (production)

#### Network Security
- No hardcoded IPs/domains
- CORS properly configured
- Database not exposed to internet
- API behind load balancer (production)

#### Environment Isolation
- Development, staging, production separate
- Different API keys per environment
- Database backups isolated
- Logs segregated by environment

---

## 11. Performance Requirements

### 11.1 Response Time SLAs

| Endpoint | Target | P95 | P99 |
|----------|--------|-----|-----|
| POST /auth/register | < 2s | 3s | 5s |
| POST /auth/login | < 1s | 2s | 3s |
| POST /sessions/ | < 1s | 1s | 2s |
| GET /sessions/ | < 1s | 1s | 2s |
| POST /documents/upload | < 60s | 90s | 120s |
| GET /documents/session/{id} | < 1s | 1s | 2s |
| **POST /chat/** | **< 30s** | **45s** | **60s** |
| GET /chat/session/{id}/history | < 5s | 10s | 15s |

### 11.2 Concurrent User Support

- Minimum 100 concurrent users
- Minimum 10 requests/second sustained
- Database connection pool: 20 connections
- Memory per user: ~100 KB (session state minimal)
- No in-memory caching of user data

### 11.3 Database Performance

#### Query Optimization
- All queries use proper indexes
- Vector similarity search uses IVFFlat index
- Lazy loading of relationships (SQLAlchemy)
- Connection pooling enabled (min 5, max 20)

#### Expected Performance
- User lookup by email: < 10ms
- Session list (10 sessions): < 50ms
- Chunk retrieval for RAG (top 4): < 100ms (with vector index)
- Conversation history (100 msgs): < 500ms
- Document upload (10 MB file, 500 chunks): < 45s

### 11.4 Scalability

#### Horizontal Scaling
- Stateless application design (no in-memory state)
- Multiple FastAPI instances possible
- Database load balancing (read replicas optional)
- Session affinity not required

#### Vertical Scaling
- CPU: 2+ cores recommended
- Memory: 2 GB minimum, 4 GB recommended
- Storage: 10 GB for 1M embeddings

### 11.5 Optimization Strategies

#### Application Level
- Async/await for I/O operations
- Connection pooling
- Request timeouts (30s connection, 120s request)
- Batch operations where possible

#### Database Level
- Index optimization
- Query analysis with EXPLAIN ANALYZE
- Slow query logging
- Connection recycling

#### API Level
- Response pagination (future)
- Compression (gzip enabled)
- Caching headers (ETag, Last-Modified future)

---

## 12. Deployment & DevOps

### 12.1 Containerization

#### Docker Image
- **Base Image:** `python:3.11-slim` (minimal size)
- **Build Time:** < 2 minutes
- **Image Size:** < 500 MB
- **Multi-stage builds:** Not needed for MVP

#### docker-compose.yml
- PostgreSQL service with pgvector
- Backend service with environment variables
- Health checks configured
- Volume mounts for development

#### Deployment Process
1. Build Docker image
2. Test locally with docker-compose
3. Push to registry (Docker Hub, ECR)
4. Deploy to production server
5. Run migrations (one-time)
6. Start container

### 12.2 Environment Configuration

#### Development
- DEBUG=true
- DATABASE_URL=postgresql://localhost/rag_chatbot_db
- CORS_ORIGINS=http://localhost:3000

#### Production
- DEBUG=false
- DATABASE_URL=postgresql://user:pass@rds-host/db
- CORS_ORIGINS=https://yourdomain.com
- LOG_LEVEL=INFO
- JWT_SECRET_KEY=(long random string)

#### Environment Variables
All configuration via environment variables:
- No hardcoded secrets
- `.env.example` provided
- `.env` in .gitignore

### 12.3 Database Migrations

#### Initial Setup
```bash
psql -U postgres -d rag_chatbot_db -f schema.sql
```

#### Deployment Strategy
- Schema created on first container start
- Idempotent migrations (safe to run multiple times)
- Backup before major schema changes
- Rollback plan documented

### 12.4 Production Hosting Options

#### Option A: Render.com (Recommended for MVP)
- **Cost:** Free tier available, pay-as-you-go
- **Setup:** Connect GitHub, auto-deploy
- **Database:** PostgreSQL add-on available
- **Pros:** Simple, automatic SSL, GitHub integration
- **Cons:** Less control, potential cold starts

#### Option B: AWS (ECS + RDS)
- **Cost:** Pay-per-use ($50-200/month)
- **Setup:** Infrastructure as Code (CloudFormation)
- **Database:** RDS PostgreSQL
- **Pros:** Maximum control, scaling, backups
- **Cons:** Complex setup, monitoring overhead

#### Option C: DigitalOcean
- **Cost:** $5-20/month (VPS)
- **Setup:** Manual or via Terraform
- **Database:** Managed PostgreSQL add-on
- **Pros:** Simple, affordable, good docs
- **Cons:** Manual scaling

### 12.5 Monitoring & Logging

#### Health Monitoring
- `/health` endpoint for uptime checks
- Container resource monitoring (CPU, memory)
- Database connection pool monitoring
- Error rate tracking

#### Logging Strategy
- All logs to stdout (docker logs)
- Structured JSON logging
- Log level: INFO (production)
- Centralized logging (CloudWatch, ELK future)

#### Alerting
- Alert on error rate > 1%
- Alert on response time > 30s
- Alert on database connection failures
- Alert on disk space > 80%

### 12.6 Backup & Disaster Recovery

#### Database Backups
- Daily automated backups (production)
- Point-in-time recovery (24 hours)
- Backup retention: 30 days
- RTO: 1 hour, RPO: 1 day

#### Data Retention
- User data retained indefinitely
- Soft-delete for compliance (user deletion marks as deleted)
- Archive old sessions (optional optimization)

#### Disaster Recovery
- Database replication enabled (production)
- Read replicas for scaling (future)
- Manual intervention for catastrophic failure

---

## 13. Quality Assurance

### 13.1 Testing Strategy

#### Unit Tests
- Test each service independently
- Mock external APIs (OpenAI)
- Test data validation
- Test error handling
- Coverage target: > 70%

#### Integration Tests
- Test API endpoints end-to-end
- Test database interactions
- Test authentication flow
- Test RAG pipeline

#### E2E Tests
- Register → Login → Create Session → Upload Doc → Chat
- Verify response accuracy
- Verify data persistence
- Critical path only

#### Performance Tests
- Load test (100 concurrent users)
- Document upload with large files
- Long conversation history retrieval
- Vector similarity search performance

### 13.2 Code Quality Standards

#### Code Style
- Black for formatting (line length: 88)
- flake8 for linting
- No warnings allowed
- Type hints for all functions

#### Documentation
- Docstrings for all classes and methods
- Inline comments for complex logic
- README with setup instructions
- API documentation with examples

#### Review Process
- Code review before merge (if team)
- Automated tests must pass
- No hardcoded secrets
- No print() statements (use logging)

### 13.3 Deployment Validation

#### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code quality checks passed
- [ ] Database migrations tested
- [ ] Docker image builds
- [ ] docker-compose up works
- [ ] E2E tests pass on staging
- [ ] Logs review for errors
- [ ] Performance tests within SLA

#### Post-Deployment
- [ ] Health check endpoint responds
- [ ] Can register and login
- [ ] Can upload document
- [ ] Can chat and receive response
- [ ] Monitor logs for 1 hour
- [ ] Performance metrics acceptable

---

## 14. Risk & Mitigation

### 14.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| OpenAI API rate limiting | High | Implement exponential backoff, queue requests |
| Database connection exhaustion | High | Connection pooling, max connections configured |
| Large embeddings storage | Medium | Compression (future), archive old data |
| LLM hallucination/incorrect responses | Medium | Proper prompt engineering, source doc attribution |
| PDF extraction errors | Medium | Fallback to text-only, user validation |
| pgvector performance degradation | Low | Proper indexing, monitor query performance |

### 14.2 Operational Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Database down | High | Automated backups, RTO 1 hour |
| API key exposure | High | Environment variables, secrets manager |
| Concurrent request spike | Medium | Rate limiting, load balancer |
| Disk space exhaustion | Medium | Monitoring, alerts, old data archival |
| Secret key compromise | High | Rotation procedure, audit logs |

### 14.3 Security Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| SQL injection | Medium | SQLAlchemy ORM (parameterized queries) |
| Unauthorized data access | High | JWT auth, user_id filtering on all queries |
| CORS misconfiguration | Medium | Whitelist trusted origins, test thoroughly |
| Brute force login | Medium | Rate limiting on auth endpoints |
| Token theft | High | HTTPS only, secure storage guidelines |

### 14.4 Schedule Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| OpenAI API integration issues | Medium | Early integration testing, fallback message |
| Database schema complexity | Low | Start simple, iterate, test frequently |
| Embedding generation speed | Medium | Use efficient model, batch processing |
| Deployment failures | High | Docker tested locally first, staging env |

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **RAG** | Retrieval Augmented Generation - combining document retrieval with LLM generation |
| **LLM** | Large Language Model (GPT-4) |
| **Embedding** | Numerical vector representation of text (1536-dimensional for OpenAI) |
| **Vector Similarity** | Cosine similarity between embedding vectors to find relevant content |
| **JWT** | JSON Web Token - stateless authentication mechanism |
| **pgvector** | PostgreSQL extension for vector data type and similarity operators |
| **Session** | User's conversation context (documents + history) |
| **Chunk** | Text segment of document (1000 chars with 200 char overlap) |
| **Contextualization** | Including relevant document chunks in LLM prompt |
| **SLA** | Service Level Agreement - guaranteed response time |
| **RTO** | Recovery Time Objective - max acceptable downtime |
| **RPO** | Recovery Point Objective - max acceptable data loss |
| **IVFFlat** | Clustering-based index type for vector similarity search |
| **ACID** | Atomicity, Consistency, Isolation, Durability - database properties |

---

## 16. Approval & Sign-Off

**Document Status:** Final  
**Last Updated:** January 24, 2026  
**Next Review:** After MVP deployment  

**Prepared By:** Development Team  
**Reviewed By:** [Name]  
**Approved By:** [Name]  

---

## Appendix A: API Examples

### Example 1: Complete User Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePass123",
    "full_name": "Test User"
  }'
# Response: {access_token, user_id}

# 2. Create session
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Research Chat"}'
# Response: {session_id}

# 3. Upload document
curl -X POST "http://localhost:8000/api/documents/upload?session_id={session_id}" \
  -H "Authorization: Bearer {token}" \
  -F "file=@document.pdf"
# Response: {chunks_created}

# 4. Send message
curl -X POST http://localhost:8000/api/chat/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "{session_id}",
    "message": "What are the main topics?"
  }'
# Response: {response, source_documents}
```

---

## Appendix B: Environment Variables Reference

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/rag_chatbot_db
DATABASE_ECHO=false

# API Keys
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# LLM Configuration
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# JWT Security
JWT_SECRET_KEY=change-this-in-production-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Application
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# RAG Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_K=4
ENABLE_COMPRESSION=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=3600
```

---

**End of SRS Document**
