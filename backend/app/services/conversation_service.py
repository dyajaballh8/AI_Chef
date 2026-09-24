import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from ..models import Conversation, Message, User, Recipe


class ConversationService:
    """
    Service managing conversation persistence and business logic.
    Enforces absolute user isolation on all operations.
    """

    @staticmethod
    def create_conversation(db: Session, user_id: int, title: str = "New Conversation") -> Conversation:
        """Create a new conversation belonging strictly to user_id."""
        conversation = Conversation(
            user_id=user_id,
            title=title or "New Conversation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_user_conversations(db: Session, user_id: int) -> List[Conversation]:
        """
        Retrieve all conversations owned strictly by user_id.
        Sorted by updated_at descending.
        """
        return db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()

    @staticmethod
    def get_user_conversation_by_id(db: Session, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """
        Retrieve a single conversation ensuring user ownership.
        Returns None if conversation does not exist or belongs to another user.
        """
        return db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

    @staticmethod
    def delete_user_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
        """
        Delete a conversation only if owned by user_id.
        Cascades deletion to all messages.
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            return False

        db.delete(conversation)
        db.commit()
        return True

    @staticmethod
    def add_message(
        db: Session,
        conversation: Conversation,
        role: str,
        content: str,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None
    ) -> Message:
        """Add a message to a conversation and update the conversation timestamp."""
        now = datetime.utcnow()
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            image_base64=image_base64,
            image_mime_type=image_mime_type,
            created_at=now
        )
        db.add(message)
        conversation.updated_at = now
        db.commit()
        db.refresh(message)
        db.refresh(conversation)
        return message

    @staticmethod
    def update_title(
        db: Session,
        conversation: Conversation,
        new_title: str
    ) -> Conversation:
        """Update conversation title."""
        conversation.title = new_title
        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def save_recipe(
        db: Session,
        user_id: int,
        conversation_id: Optional[int],
        title: str,
        content: str,
        ingredients: Optional[str] = None,
        instructions: Optional[str] = None,
        cooking_time: Optional[str] = None,
        difficulty: Optional[str] = None,
    ) -> Recipe:
        """Persist a structured recipe returned by Chef AI into the database."""
        recipe = Recipe(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title.strip()[:150] or "Recipe",
            content=content,
            ingredients=ingredients,
            instructions=instructions,
            cooking_time=cooking_time,
            difficulty=difficulty,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        return recipe

    @staticmethod
    def build_recipe_json(recipe: Recipe) -> str:
        """
        Build the structured JSON snapshot stored on the message row once a
        recipe is approved (see Message.recipe_json). Keeps the same shape
        used elsewhere in the project: dish_name / cooking_time / difficulty
        / ingredients / instructions.
        """
        ingredients = [
            line.strip("-* ").strip()
            for line in (recipe.ingredients or "").splitlines()
            if line.strip()
        ]
        instructions = [
            line.strip()
            for line in (recipe.instructions or "").splitlines()
            if line.strip()
        ]

        payload = {
            "dish_name": recipe.title,
            "cooking_time": recipe.cooking_time,
            "difficulty": recipe.difficulty,
            "ingredients": ingredients,
            "instructions": instructions,
            "recipe_id": recipe.id,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def attach_recipe_json_to_message(db: Session, message: Message, recipe_json: str) -> Message:
        """Stamp the approved recipe's structured JSON onto its source message."""
        message.recipe_json = recipe_json
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def extract_recipe_fields(recipe_text: str) -> dict:
        """Very lightweight parser to store the recipe content in a structured way."""
        title = "Recipe"
        lines = [line.strip() for line in (recipe_text or "").splitlines() if line.strip()]
        for line in lines:
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break

        ingredients = None
        instructions = None
        cooking_time = None
        difficulty = None

        for idx, line in enumerate(lines):
            if line.lower().startswith("**cooking time:**"):
                cooking_time = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.lower().startswith("**difficulty:**"):
                difficulty = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.lower().startswith("###") and "ingredient" in line.lower():
                ingredients = "\n".join(lines[idx + 1: idx + 5]) if idx + 1 < len(lines) else None
            elif line.lower().startswith("###") and "step" in line.lower():
                instructions = "\n".join(lines[idx + 1:]) if idx + 1 < len(lines) else None

        return {
            "title": title,
            "content": recipe_text,
            "ingredients": ingredients,
            "instructions": instructions,
            "cooking_time": cooking_time,
            "difficulty": difficulty,
        }

    @staticmethod
    def seed_sample_conversations(db: Session, user: User) -> List[Conversation]:
        """Seed pre-made culinary conversations for testing and demonstration."""
        samples = [
            {
                "title": "Italian Dinner 🍝",
                "messages": [
                    {"role": "user", "content": "Give me an authentic recipe for homemade lasagna."},
                    {"role": "assistant", "content": "# 🍳 Classic Italian Beef & Ricotta Lasagna\n\n**Cooking Time:** 1 hour 15 minutes | **Difficulty:** Medium\n\n### 🛒 Ingredients\n- Lasagna sheets — 12 sheets\n- Ground beef — 600 g\n- Crushed tomatoes — 800 g\n- Ricotta cheese — 450 g\n- Mozzarella — 350 g\n\n### 👩🍳 Cooking Steps\n1. Prepare rich bolognese sauce and simmer for 20 minutes.\n2. Layer sauce, pasta sheets, ricotta, and mozzarella.\n3. Bake at 375°F (190°C) for 40 minutes until bubbly.\n\n### 💡 Chef's Pro Tips\n- Let rest 15 minutes before slicing for clean, intact layers!"}
                ]
            },
            {
                "title": "Healthy Lunch Ideas 🥗",
                "messages": [
                    {"role": "user", "content": "What is a quick healthy lunch high in protein?"},
                    {"role": "assistant", "content": "# 🥗 Mediterranean Quinoa & Grilled Lemon Chicken Bowl\n\n**Cooking Time:** 20 minutes | **Difficulty:** Easy\n\n### 🛒 Ingredients\n- Chicken breast — 250 g (grilled & sliced)\n- Cooked quinoa — 1 cup\n- Cucumbers & Cherry tomatoes — 1 cup diced\n- Feta cheese — 40 g\n- Extra virgin olive oil & lemon juice — 2 tbsp\n\n### 💡 Chef's Pro Tips\n- Cook quinoa in vegetable broth instead of plain water for extra savoriness!"}
                ]
            },
            {
                "title": "Birthday Cake 🍰",
                "messages": [
                    {"role": "user", "content": "How do I make a soft vanilla birthday cake from scratch?"},
                    {"role": "assistant", "content": "# 🎂 Classic Golden Vanilla Celebration Cake\n\n**Cooking Time:** 45 minutes | **Difficulty:** Medium\n\n### 🛒 Ingredients\n- Flour — 2.5 cups\n- Granulated sugar — 1.5 cups\n- Unsalted butter — 1 cup (room temp)\n- Large eggs — 3\n- Pure vanilla extract — 1 tbsp\n\n### 💡 Chef's Pro Tips\n- Never frost warm cake layers; chill them in the fridge first to prevent frosting from sliding!"}
                ]
            },
            {
                "title": "Chicken Recipes 🍗",
                "messages": [
                    {"role": "user", "content": "I have chicken, rice and tomatoes. What can I cook?"},
                    {"role": "assistant", "content": "# 🍳 One-Pot Mediterranean Chicken & Tomato Rice\n\n**Cooking Time:** 35 minutes | **Difficulty:** Easy\n\n### 🛒 Ingredients\n- Chicken thighs — 500 g\n- Basmati rice — 1.5 cups\n- Ripe tomatoes — 3 medium diced\n- Onion & garlic — 1 each\n- Chicken broth — 2.5 cups\n\n### 💡 Chef's Pro Tips\n- Sear chicken first to render flavor into the pan before adding aromatics and rice."}
                ]
            },
            {
                "title": "Egyptian Food 🥘",
                "messages": [
                    {"role": "user", "content": "How can I make authentic Egyptian Hawawshi at home?"},
                    {"role": "assistant", "content": "# 🥘 Authentic Egyptian Hawawshi (Spiced Meat Pita)\n\n**Cooking Time:** 30 minutes | **Difficulty:** Easy\n\n### 🛒 Ingredients\n- Fresh baladi bread or pita — 4 loaves\n- Minced beef (20% fat) — 500 g\n- Grated onions — 2 medium\n- Green peppers & chili — 2 finely minced\n- Hawawshi spices (allspice, coriander, cumin, cinnamon) — 2 tsp\n\n### 💡 Chef's Pro Tips\n- Brush the exterior of the pita generously with ghee or olive oil for maximum crunch!"}
                ]
            }
        ]

        created_convos = []
        for s in samples:
            convo = Conversation(
                user_id=user.id,
                title=s["title"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(convo)
            db.commit()
            db.refresh(convo)

            for m in s["messages"]:
                msg = Message(
                    conversation_id=convo.id,
                    role=m["role"],
                    content=m["content"],
                    created_at=datetime.utcnow()
                )
                db.add(msg)
            db.commit()
            created_convos.append(convo)

        return created_convos
