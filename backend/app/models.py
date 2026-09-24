from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Conversation.updated_at)"
    )
    recipes = relationship(
        "Recipe",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Recipe.updated_at)"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), default="New Conversation", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    recipes = relationship(
        "Recipe",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="desc(Recipe.updated_at)"
    )


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(150), nullable=False, default="Recipe")
    content = Column(Text, nullable=False)
    ingredients = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    cooking_time = Column(String(80), nullable=True)
    difficulty = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="recipes")
    conversation = relationship("Conversation", back_populates="recipes")


class Message(Base):
    """Message entity model belonging to a specific conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    image_base64 = Column(Text, nullable=True)  # optional base64 image attached by the user
    image_mime_type = Column(String(50), nullable=True)
    # Structured JSON snapshot of the recipe this message represents, filled
    # in only once the user Approves saving it (see chat.py /recipe-decision).
    # Stays NULL for plain chat messages and for rejected/unapproved recipes.
    recipe_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


    conversation = relationship("Conversation", back_populates="messages")
