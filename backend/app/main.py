import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

# استيراد مطلق بدلاً من النسبي لضمان بيئة Vercel Serverless
try:
    from app.database import engine, Base
    from app.routers import auth, conversations, chat
except ImportError:
    from database import engine, Base
    from routers import auth, conversations, chat


def _run_lightweight_migrations():
    """
    إجراء المايجريشن بأمان
    """
    try:
        inspector = inspect(engine)
        if "messages" in inspector.get_table_names():
            existing_columns = {col["name"] for col in inspector.get_columns("messages")}
            if "recipe_json" not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN recipe_json TEXT"))
    except Exception as e:
        print(f"Migration skip/error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # تشغيل إنشاء الجداول دون إيقاف السيرفر في حال وجود تأخير
    try:
        Base.metadata.create_all(bind=engine)
        _run_lightweight_migrations()
    except Exception as e:
        print(f"DB Startup warning: {e}")
    yield


app = FastAPI(
    title="Chef AI Assistant 🍳",
    description="Production-grade AI-powered culinary assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "app": "Chef AI Assistant 🍳",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "chef-ai-assistant"}