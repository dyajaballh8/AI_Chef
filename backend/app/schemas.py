from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict


# ==============================================================================
# Auth Schemas
# ==============================================================================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username must be 3-50 characters")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, max_length=128, description="Password must be at least 6 characters")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty or only whitespace")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain alphanumeric characters, underscores, or hyphens")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v.strip()) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserLogin(BaseModel):
    login: str = Field(..., description="Username or email address")
    password: str = Field(..., min_length=1, description="Password")

    @field_validator("login")
    @classmethod
    def validate_login(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Login identifier cannot be empty")
        return v


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None


# ==============================================================================
# Message Schemas
# ==============================================================================

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message text")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        return v


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime
    image_base64: Optional[str] = Field(default=None, description="Base64 image attached to this message, if any")
    image_mime_type: Optional[str] = None
    recipe_json: Optional[str] = Field(
        default=None,
        description="Structured JSON snapshot of the recipe (dish_name, ingredients, instructions, ...), set only after the user approves saving it."
    )

    model_config = ConfigDict(from_attributes=True)


class ChatMessageRequest(BaseModel):
    content: str = Field(default="", max_length=10000, description="Prompt or query for the AI Chef")
    image_base64: Optional[str] = Field(
        default=None,
        description="Optional base64-encoded image (no data: prefix) for Chef AI to analyze, e.g. a photo of ingredients or food packaging."
    )
    image_mime_type: Optional[str] = Field(
        default="image/jpeg",
        description="MIME type of the attached image, e.g. image/jpeg or image/png"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return (v or "").strip()

    @model_validator(mode="after")
    def validate_has_content_or_image(self):
        if not self.content and not self.image_base64:
            raise ValueError("Message must contain text content, an attached image, or both.")
        return self


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    recipe_pending: bool = Field(
        default=False,
        description=(
            "True when the assistant reply looks like a recipe and is awaiting "
            "the user's Approve/Reject decision before it is saved to SQLite "
            "(see POST /conversations/{id}/messages/{message_id}/recipe-decision)."
        )
    )


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=150)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> str:
        if v is None or not v.strip():
            return "New Conversation"
        return v.strip()


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RecipeResponse(BaseModel):
    id: int
    user_id: int
    conversation_id: Optional[int] = None
    title: str
    content: str
    ingredients: Optional[str] = None
    instructions: Optional[str] = None
    cooking_time: Optional[str] = None
    difficulty: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Human-in-the-Loop Recipe Approval Schemas
# ==============================================================================

class RecipeDecisionRequest(BaseModel):
    approve: bool = Field(..., description="True to Approve saving the recipe to SQLite, False to Reject it.")


class RecipeDecisionResponse(BaseModel):
    saved: bool
    recipe: Optional[RecipeResponse] = None
    message: str
