import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables explicitly from the backend .env file.
BACKEND_ENV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(BACKEND_ENV)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chef_ai.db")

# SQLite specific connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides an isolated SQLAlchemy database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
