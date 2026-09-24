# Chef AI Assistant — Backend 🍳

FastAPI backend for Chef AI Assistant with JWT authentication, SQLite storage, conversation isolation, and AI Chef integration.

## Features
- **JWT Authentication:** Password hashing using PBKDF2-HMAC-SHA256 and signed bearer tokens.
- **Strict Data Isolation:** Users cannot query or mutate other users' conversations or message records.
- **Modular AI Service:** Direct `httpx` integration with Google Gemini, OpenAI, or intelligent Chef fallback.
- **Auto Conversation Titles:** Intelligent title generation on the first query.
- **RESTful Endpoints & Swagger:** Automatically documented at `/docs`.

## Setup & Run

1. **Create and Activate Virtual Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Copy `.env.example` to `.env` and set your preferred keys:
   ```bash
   cp .env.example .env
   ```

4. **Start the Development Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Access Interactive Documentation:**
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
