# Chef AI Assistant 🍳

An AI-powered culinary web application where users can create accounts, manage multiple private conversations, and chat with an intelligent AI Chef for customized recipes, ingredient substitutions, and cooking advice.

Built with **FastAPI**, **SQLAlchemy**, **SQLite**, and **Vanilla HTML5/CSS3/JavaScript**.

---

## 🌟 Features

- **🔐 Secure User Authentication:** Register and login with secure password hashing (PBKDF2-HMAC-SHA256 with 100,000 rounds) and signed JWT tokens.
- **🛡️ Strict Data Isolation:** Every conversation and message is strictly isolated to its owner. Users can never view, update, delete, or send messages to another user's conversation. Any unauthorized access returns a `404 Not Found`.
- **💬 Multi-Conversation Management:** Create, view, search, and delete multiple independent conversation threads (e.g. *Italian Dinner 🍝*, *Egyptian Food 🥘*, *Birthday Cake 🍰*).
- **🤖 LangChain-Powered Chef Agent:**
  - Built with **LangChain** (`init_chat_model` + `create_agent`) on top of **Google Gemini**.
  - Full per-conversation memory: prior messages from the database are replayed into the agent on every call so the Chef always remembers the conversation.
  - Graceful fallback message if the AI request fails (network/quota issues) so the app never breaks.
- **📷 Multimodal — Chef AI Can See Images:**
  - Attach a photo (e.g. ingredients, a food package, a finished dish) using the 📷 button next to the chat box.
  - The image is sent to the LangChain agent as a multimodal message (text + image), and Chef AI answers using what it sees — e.g. suggests recipes based on visible ingredients.
  - Images are stored per-message so they reappear when you reopen a conversation.
  - A sample image (`frontend/assets/sample-ingredients.jpg`) is bundled in the project — click the **"📷 Try an Image"** suggestion card to test it instantly.
- **📋 Structured Recipe Format:** Every recipe generated includes:
  - Recipe Name & Badges (Cooking Time, Difficulty)
  - Ingredients with exact quantities and units
  - Step-by-Step cooking instructions
  - Chef's Pro Tips & substitutions
- **⚡ Automatic Conversation Titles:** Conversations automatically update from *"New Conversation"* to a relevant, catchy culinary title (e.g. *"Chicken & Rice Ideas 🍗"*, *"Classic Lasagna 🍝"*) upon the first prompt.
- **📱 Modern Cooking-Themed UI:** Responsive desktop & mobile layout with side drawer, rich markdown rendering for recipes, quick starter prompt chips, and loading states (*"Chef is cooking... 👨🍳"*).

---

## 🏗️ Project Structure

```
chef-ai-assistant/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI initialization, CORS, and routing
│   │   ├── database.py              # SQLite engine & SessionLocal
│   │   ├── models.py                # SQLAlchemy Models: User, Conversation, Message
│   │   ├── schemas.py               # Pydantic schemas & validation
│   │   ├── auth.py                  # Password hashing & JWT creation/verification
│   │   ├── dependencies.py          # get_current_user & get_db dependencies
│   │   ├── ai_service.py            # LangChain Chef agent (init_chat_model + create_agent), multimodal
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # /auth/register, /auth/login, /auth/me
│   │   │   ├── conversations.py     # /conversations CRUD & /seed-samples
│   │   │   └── chat.py              # /conversations/{id}/messages
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       └── conversation_service.py # Database logic & user isolation
│   │
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env                         # Local environment variables
│   └── README.md
│
├── frontend/
│   ├── index.html                   # Main chat dashboard (now with image attach button)
│   ├── login.html                   # Sign-in page
│   ├── register.html                # Registration page
│   ├── app.js                       # Chat controller, Markdown parser & image attach/preview
│   ├── auth.js                      # Token management & API client
│   ├── styles.css                   # Culinary-themed responsive styling
│   └── assets/
│       └── sample-ingredients.jpg   # Bundled sample photo for testing image understanding
│
├── tests/
│   ├── __init__.py
│   └── test_app.py                  # Automated test suite (Auth, CRUD, Isolation)
│
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Modern Web Browser (Chrome, Firefox, Edge, Safari)

### 2. Create & Activate Virtual Environment

```bash
# Navigate to the backend directory
cd chef-ai-assistant/backend

# Create virtual environment
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate

# Activate on macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The project includes a `.env` file pre-configured for local testing. You can customize keys in `backend/.env`:

```env
SECRET_KEY=chef_ai_super_secret_jwt_key_9f8d7e6c5b4a312098471234
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./chef_ai.db

# Add your Gemini API Key (used by LangChain's init_chat_model):
GOOGLE_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-3.6-flash
```

*(Note: A valid `GOOGLE_API_KEY` is required — the Chef agent is built with LangChain on top of Gemini.)*

### 5. Run the Backend

```bash
# From inside chef-ai-assistant/backend
uvicorn app.main:app --reload --port 8000
```

The database tables are **automatically created on startup** in `chef_ai.db`.

> ⚠️ If you're upgrading an existing `chef_ai.db` from before the image-attachment feature, delete it (or the `Message` table won't have the new `image_base64` columns) so it gets recreated with the updated schema.

### 6. Open the Application

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)** (or `http://127.0.0.1:8000/login`)

You can also double-click `frontend/login.html` directly in your file explorer to test via file origin!

---

## 📖 Interactive API Documentation (Swagger)

FastAPI automatically generates interactive documentation:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

A comprehensive test suite is included in `tests/test_app.py`, verifying:
1. **User Registration & Login** (email validation, password length, JWT token issuing)
2. **Duplicate Prevention** (unique email and username rejection)
3. **Conversation CRUD** (create, list, get, delete)
4. **MANDATORY SECURITY TEST:** Strict User Data Isolation
   - Creates User A (`Dyaa`) and User B (`Ahmed`).
   - Confirms User A and User B only see their respective conversations.
   - Confirms User A receives `404 Not Found` when attempting to read, message, or delete User B's conversation.
   - Confirms User B receives `404 Not Found` when attempting to access User A's conversation.
5. **AI Chef & Auto-Titles** (Context preservation, structured recipe format, auto-title generation).

To run the tests:

```bash
# From chef-ai-assistant/
pytest tests/test_app.py -v
```

---

## 🍳 Sample Demo Conversations

For rapid testing and demonstration, you can load sample conversations for your account by clicking the **"✨ Sample Chats"** button in the chat header, or calling:
```http
POST /conversations/seed-samples
Authorization: Bearer <token>
```

This immediately loads:
- **Italian Dinner 🍝** (Homemade Lasagna)
- **Healthy Lunch Ideas 🥗** (Quinoa Lemon Chicken Bowl)
- **Birthday Cake 🍰** (Vanilla Celebration Cake)
- **Chicken Recipes 🍗** (One-Pot Mediterranean Chicken & Rice)
- **Egyptian Food 🥘** (Authentic Egyptian Hawawshi)
