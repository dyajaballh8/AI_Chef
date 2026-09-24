import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

# معالجة الشاملة للاستيراد لمنع أخطاء ImportError في Vercel Serverless
try:
    from app.database import engine, Base
    from app.routers import auth, conversations, chat
except ImportError:
    try:
        from database import engine, Base
        from routers import auth, conversations, chat
    except ImportError:
        from .database import engine, Base
        from .routers import auth, conversations, chat


def _run_lightweight_migrations():
    """
    التأكد من وجود الأعمدة المطلوبة دون إيقاف السيرفر في حالة وجود استثناءات
    """
    try:
        inspector = inspect(engine)
        if "messages" in inspector.get_table_names():
            existing_columns = {col["name"] for col in inspector.get_columns("messages")}
            if "recipe_json" not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN recipe_json TEXT"))
    except Exception as e:
        print(f"Migration warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # حماية عملية إنشاء الجدول لمنع إسقاط السيرفر بـ Timeout في Vercel
    try:
        Base.metadata.create_all(bind=engine)
        _run_lightweight_migrations()
    except Exception as e:
        print(f"Database setup warning: {e}")
    yield


app = FastAPI(
    title="Chef AI Assistant 🍳",
    description="Production-grade AI-powered culinary assistant with multi-user conversation isolation and recipe generation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# إعدادات CORS للسماح لجميع المصادر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط الـ Routers
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