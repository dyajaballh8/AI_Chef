from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Message, Recipe
from ..schemas import ChatMessageRequest, ChatResponse, RecipeDecisionRequest, RecipeDecisionResponse
from ..dependencies import get_current_user
from ..services.conversation_service import ConversationService
from ..ai_service import ai_service

router = APIRouter(prefix="/conversations", tags=["Chat"])


def _looks_like_recipe(reply_text: str) -> bool:
    """Heuristic check: does this AI Chef reply look like a recipe?"""
    lower_reply = (reply_text or "").lower()
    return "ingredients" in lower_reply or "recipe" in lower_reply or "cooking time" in lower_reply


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
def send_message_to_conversation(
    conversation_id: int,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to Chef AI within a specific conversation.
    - Strictly checks ownership: returns 404 if conversation doesn't belong to current_user.
    - Maintains conversation context without leaking between conversations or users.
    - Generates and updates conversation title automatically on first prompt.
    - Saves user query and AI Chef response to database.
    """
    # 1. Verify ownership strictly
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

    user_text = request.content.strip()
    has_image = bool(request.image_base64)

    if not user_text and not has_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # 2. Extract conversation context history (isolated to this conversation only)
    history_messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    formatted_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages
        if m.role in ["user", "assistant"]
    ]

    # 3. Save user message to database (including the image, if attached)
    stored_text = user_text or "🖼️ (Image attached)"
    user_msg = ConversationService.add_message(
        db=db,
        conversation=conversation,
        role="user",
        content=stored_text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type
    )

    # 4. Auto-generate title if this is the first message or title is default
    if conversation.title in ["New Conversation", "", None] or len(history_messages) == 0:
        new_title = ai_service.generate_conversation_title(stored_text)
        ConversationService.update_title(db, conversation, new_title)

    # 5. Generate response from AI Chef (LangChain agent, multimodal-aware)
    try:
        chef_reply = ai_service.generate_response(
            conversation_history=formatted_history,
            user_message=user_text,
            image_base64=request.image_base64,
            image_mime_type=request.image_mime_type,
            conversation_id=conversation.id,
        )
    except Exception as e:
        chef_reply = (
            "⚠️ **Chef AI Notice:** I encountered a temporary connection issue. "
            "However, please try asking again in a moment!"
        )

    # Trim Message: strip any stray leading/trailing whitespace from the AI
    # Chef reply before it is stored or evaluated any further.
    chef_reply = (chef_reply or "").strip()

    # 6. Save AI Chef response to database
    assistant_msg = ConversationService.add_message(
        db=db,
        conversation=conversation,
        role="assistant",
        content=chef_reply
    )

    # 7. Human-in-the-Loop for SQLite: if the reply looks like a recipe, do
    # NOT save it automatically. Just flag it as pending — the frontend will
    # ask the user to Approve/Reject, and only /recipe-decision actually
    # writes to the database.
    recipe_pending = _looks_like_recipe(chef_reply)

    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "recipe_pending": recipe_pending
    }


@router.post(
    "/{conversation_id}/messages/{message_id}/recipe-decision",
    response_model=RecipeDecisionResponse
)
def decide_on_recipe_save(
    conversation_id: int,
    message_id: int,
    decision: RecipeDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Human-in-the-Loop for SQLite persistence.

    After Chef AI proposes a recipe, the user must explicitly Approve or
    Reject saving it to the SQLite `recipes` table. Nothing is written to
    the database unless `approve=True` is received here.
    """
    # Verify conversation ownership strictly.
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

    # Verify the message exists, belongs to this conversation, and is an
    # assistant reply (only Chef AI replies can be saved as recipes).
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation.id,
        Message.role == "assistant"
    ).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found in this conversation."
        )

    if not decision.approve:
        return RecipeDecisionResponse(
            saved=False,
            recipe=None,
            message="Recipe was rejected and was not saved."
        )

    # Avoid saving the same message's recipe twice if the user double-clicks.
    existing = db.query(Recipe).filter(
        Recipe.user_id == current_user.id,
        Recipe.conversation_id == conversation.id,
        Recipe.content == message.content
    ).first()
    if existing:
        if not message.recipe_json:
            recipe_json = ConversationService.build_recipe_json(existing)
            ConversationService.attach_recipe_json_to_message(db, message, recipe_json)
        return RecipeDecisionResponse(
            saved=True,
            recipe=existing,
            message="Recipe was already saved."
        )

    recipe = ai_service.save_recipe_from_response(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        recipe_text=message.content,
    )

    # Stamp the structured recipe JSON onto the source message too, so the
    # `messages` table keeps a snapshot alongside the dedicated recipes table.
    recipe_json = ConversationService.build_recipe_json(recipe)
    ConversationService.attach_recipe_json_to_message(db, message, recipe_json)

    return RecipeDecisionResponse(
        saved=True,
        recipe=recipe,
        message="Recipe approved and saved to the database."
    )
