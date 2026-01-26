# 🤖 RAG Chatbot API (Hybrid Architecture)

A production-grade REST API service that enables users to upload documents and interact with an AI chatbot using Retrieval Augmented Generation (RAG).

**Architecture:**
-   **LLM**: Google Gemini Pro (Free Tier)
-   **Embeddings**: Local HuggingFace (`all-MiniLM-L6-v2`) - *Zero Cost, No Rate Limits*
-   **Database**: PostgreSQL + `pgvector`
-   **Backend**: FastAPI (Python 3.11)

## ✨ Features
-   **Robust Document Pipeline**: Upload PDF/TXT files; automatically chunked and vectorized locally.
-   **Free & Scalable**: Uses local CPU-based embeddings to avoid API quotas on uploads.
-   **Smart Chat**: Context-aware responses using Google Gemini Pro.
-   **Security**: Full JWT Authentication and User Management.
-   **Session Management**: Organized chat sessions with history tracking.
-   **Containerized**: Fully Dockerized for easy deployment.

## 🚀 Quick Start (Docker)

The easiest way to run the complete project.

1.  **Configure Environment**:
    Ensure your `.env` file has a valid Google API Key:
    ```bash
    GOOGLE_API_KEY=AIzaSy...
    DATABASE_URL=postgresql://postgres:postgres@db:5432/rag_chatbot_db
    ```

2.  **Build & Run**:
    ```bash
    docker-compose up --build
    ```
    *Note: First run takes a few minutes to download the ML models.*

3.  **Access**:
    -   **API**: `http://localhost:8000`
    -   **Docs**: `http://localhost:8000/docs` (Swagger UI)

## 🛠️ Local Development

If you prefer running without Docker:

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Database**:
    You need a Postgres instance running with `pgvector` extension enabled.

3.  **Run Application**:
    ```bash
    # Reset DB (First time only)
    python reset_db.py
    
    # Start Server
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    ```

## 📚 API Endpoints

### Auth
-   `POST /api/auth/register` - Create account
-   `POST /api/auth/login` - Get Access Token

### Documents (RAG)
-   `POST /api/documents/upload?session_id={id}` - Upload File (Local Vectorization)
-   `GET /api/documents/{session_id}` - List Session Files

### Chat
-   `POST /api/sessions/` - Create Chat Session
-   `POST /api/chat/` - Send Message (Uses Gemini + Retrieved Context)

