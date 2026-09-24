import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import inspect, text

from .database import engine, Base
from .routers import auth, conversations, chat


def _run_lightweight_migrations():
    """
    Base.metadata.create_all() only creates missing tables — it never alters
    an existing one. Since chef_ai.db already existed before the
    `messages.recipe_json` column was added to the model, add it here at
    startup if it's missing, so existing data/rows are kept as-is.
    """
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("messages")}
    if "recipe_json" not in existing_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN recipe_json TEXT"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()
    yield

app = FastAPI(
    title="Chef AI Assistant 🍳",
    description="Production-grade AI-powered culinary assistant with multi-user conversation isolation and recipe generation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "null",  # file:// origins
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Chef AI Assistant API is running. Visit /docs for Swagger UI."}

    @app.get("/login", include_in_schema=False)
    async def serve_login():
        login_file = os.path.join(frontend_dir, "login.html")
        if os.path.exists(login_file):
            return FileResponse(login_file)
        return RedirectResponse(url="/docs")

    @app.get("/register", include_in_schema=False)
    async def serve_register():
        reg_file = os.path.join(frontend_dir, "register.html")
        if os.path.exists(reg_file):
            return FileResponse(reg_file)
        return RedirectResponse(url="/docs")
else:
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
