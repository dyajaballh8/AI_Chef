from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Recipe
from ..schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    RecipeResponse,
)
from ..dependencies import get_current_user
from ..services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation belonging strictly to the authenticated user.
    Frontend user_id is ignored to prevent privilege escalation.
    """
    title = payload.title if payload and payload.title else "New Conversation"
    conversation = ConversationService.create_conversation(
        db=db,
        user_id=current_user.id,
        title=title
    )
    return conversation


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all conversations belonging to the authenticated user.
    Strictly isolated: users never see other users' conversations.
    Ordered by updated_at descending.
    """
    conversations = ConversationService.get_user_conversations(
        db=db,
        user_id=current_user.id
    )
    return conversations


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve conversation details and full message history.
    Enforces user isolation: Returns 404 Not Found if the conversation does not exist
    OR belongs to another user.
    """
    conversation = ConversationService.get_user_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied."
        )
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and its messages.
    Only the verified owner can delete their conversation.
    """
    success = ConversationService.delete_user_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied."
        )
    return {"message": "Conversation successfully deleted", "id": conversation_id}


@router.get("/recipes/last", response_model=RecipeResponse)
def get_last_recipe(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return the most recent recipe saved for the current authenticated user.
    """
    recipe = db.query(Recipe).filter(Recipe.user_id == current_user.id).order_by(Recipe.updated_at.desc()).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No saved recipe found for this user."
        )
    return recipe


@router.post("/seed-samples", response_model=List[ConversationResponse])
def seed_sample_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Helper endpoint to populate sample culinary conversations for the current user.
    Creates: Italian Dinner, Healthy Lunch Ideas, Birthday Cake, Chicken Recipes, Egyptian Food.
    """
    created = ConversationService.seed_sample_conversations(db=db, user=current_user)
    return created
