import os
import sys
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.database import Base, get_db
from app.models import User, Conversation, Message, Recipe
from app.ai_service import AIService

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_ai_service_accepts_any_non_empty_google_key():
    service = AIService()
    service.google_api_key = "any-string-key"

    # This should no longer fail just because the key doesn't start with 'AIza'.
    service._validate_google_key()


# ==============================================================================
# Helper Functions
# ==============================================================================

def register_user(username: str, email: str, password: str = "password123"):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password}
    )
    return response


def login_user(login: str, password: str = "password123"):
    response = client.post(
        "/auth/login",
        json={"login": login, "password": password}
    )
    return response


# ==============================================================================
# Authentication Tests
# ==============================================================================

def test_register_user_success():
    resp = register_user("testuser1", "user1@example.com", "securepass123")
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser1"
    assert data["user"]["email"] == "user1@example.com"


def test_login_user_success():
    # Login via username
    resp = login_user("testuser1", "securepass123")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    # Login via email
    resp_email = login_user("user1@example.com", "securepass123")
    assert resp_email.status_code == 200
    assert "access_token" in resp_email.json()


def test_invalid_password():
    resp = login_user("testuser1", "wrongpassword")
    assert resp.status_code == 401
    assert "Invalid email/username or password" in resp.json()["detail"]


def test_duplicate_email():
    resp = register_user("newuser", "user1@example.com", "password123")
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_duplicate_username():
    resp = register_user("testuser1", "different@example.com", "password123")
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"]


# ==============================================================================
# Conversation CRUD Tests
# ==============================================================================

def test_conversation_crud():
    # Login user
    login_resp = login_user("testuser1", "securepass123")
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create conversation
    create_resp = client.post(
        "/conversations",
        json={"title": "Italian Dinner"},
        headers=headers
    )
    assert create_resp.status_code == 201
    convo = create_resp.json()
    assert convo["title"] == "Italian Dinner"
    convo_id = convo["id"]

    # 2. List conversations
    list_resp = client.get("/conversations", headers=headers)
    assert list_resp.status_code == 200
    convos = list_resp.json()
    assert any(c["id"] == convo_id for c in convos)

    # 3. Get single conversation
    get_resp = client.get(f"/conversations/{convo_id}", headers=headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == convo_id
    assert detail["title"] == "Italian Dinner"
    assert "messages" in detail

    # 4. Delete conversation
    del_resp = client.delete(f"/conversations/{convo_id}", headers=headers)
    assert del_resp.status_code == 200

    # 5. Confirm deletion
    get_del = client.get(f"/conversations/{convo_id}", headers=headers)
    assert get_del.status_code == 404


# ==============================================================================
# MANDATORY SECURITY TEST: Strict User Data Isolation
# ==============================================================================

def test_user_data_isolation_security():
    """
    MANDATORY REQUIREMENT:
    Create User A (Dyaa) and User B (Ahmed).
    Verify User A can access their own conversations.
    Verify User B can access their own conversations.
    Verify User A CANNOT access, read, message, or delete User B's conversations.
    Verify User B CANNOT access, read, message, or delete User A's conversations.
    """
    # 1. Register and login User A (Dyaa)
    register_user("Dyaa", "dyaa@chefai.com", "password123")
    login_a = login_user("Dyaa", "password123")
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register and login User B (Ahmed)
    register_user("Ahmed", "ahmed@chefai.com", "password123")
    login_b = login_user("Ahmed", "password123")
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates conversations: "Italian Dinner" and "Egyptian Food"
    convo_a1 = client.post("/conversations", json={"title": "Italian Dinner"}, headers=headers_a).json()
    convo_a2 = client.post("/conversations", json={"title": "Egyptian Food"}, headers=headers_a).json()

    # 4. User B creates conversations: "Chicken Recipes" and "Birthday Cake"
    convo_b1 = client.post("/conversations", json={"title": "Chicken Recipes"}, headers=headers_b).json()
    convo_b2 = client.post("/conversations", json={"title": "Birthday Cake"}, headers=headers_b).json()

    # 5. Verify User A lists ONLY User A's conversations
    list_a = client.get("/conversations", headers=headers_a).json()
    titles_a = [c["title"] for c in list_a]
    assert "Italian Dinner" in titles_a
    assert "Egyptian Food" in titles_a
    assert "Chicken Recipes" not in titles_a
    assert "Birthday Cake" not in titles_a

    # 6. Verify User B lists ONLY User B's conversations
    list_b = client.get("/conversations", headers=headers_b).json()
    titles_b = [c["title"] for c in list_b]
    assert "Chicken Recipes" in titles_b
    assert "Birthday Cake" in titles_b
    assert "Italian Dinner" not in titles_b
    assert "Egyptian Food" not in titles_b

    # 7. Verify User A CANNOT GET User B's conversation (Must return 404)
    access_attempt_a = client.get(f"/conversations/{convo_b1['id']}", headers=headers_a)
    assert access_attempt_a.status_code == 404

    # 8. Verify User B CANNOT GET User A's conversation (Must return 404)
    access_attempt_b = client.get(f"/conversations/{convo_a1['id']}", headers=headers_b)
    assert access_attempt_b.status_code == 404

    # 9. Verify User A CANNOT send a message into User B's conversation
    msg_attempt_a = client.post(
        f"/conversations/{convo_b1['id']}/messages",
        json={"content": "Hacking Ahmed's conversation"},
        headers=headers_a
    )
    assert msg_attempt_a.status_code == 404

    # 10. Verify User A CANNOT delete User B's conversation
    del_attempt_a = client.delete(f"/conversations/{convo_b1['id']}", headers=headers_a)
    assert del_attempt_a.status_code == 404

    # 11. Verify User B can still access their own conversation intact
    owner_access_b = client.get(f"/conversations/{convo_b1['id']}", headers=headers_b)
    assert owner_access_b.status_code == 200
    assert owner_access_b.json()["title"] == "Chicken Recipes"


# ==============================================================================
# Chat & Recipe Generation Test
# ==============================================================================

def test_last_recipe_route_returns_latest_recipe_for_current_user():
    login_resp = login_user("Dyaa", "password123")
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == "Dyaa").first()
        recipe = Recipe(
            user_id=user.id,
            conversation_id=None,
            title="Lasagna",
            content="# Lasagna\n\nIngredients\n- Pasta\n- Sauce\n- Cheese",
            ingredients="- Pasta\n- Sauce\n- Cheese",
            instructions="Bake it in the oven.",
            cooking_time="45 minutes",
            difficulty="Easy",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(recipe)
        db.commit()
    finally:
        db.close()

    resp = client.get("/conversations/recipes/last", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Lasagna"
    assert data["content"].startswith("# Lasagna")


def test_chat_message_and_recipe_flow():
    # Login User A
    login_resp = login_user("Dyaa", "password123")
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create new conversation with default title
    new_convo = client.post("/conversations", json={"title": "New Conversation"}, headers=headers).json()
    convo_id = new_convo["id"]

    # Send recipe query
    msg_resp = client.post(
        f"/conversations/{convo_id}/messages",
        json={"content": "Give me a recipe for lasagna."},
        headers=headers
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert "user_message" in data
    assert "assistant_message" in data
    assert "lasagna" in data["user_message"]["content"].lower()

    # Verify structured assistant recipe contents
    chef_reply = data["assistant_message"]["content"]
    assert "Ingredients" in chef_reply or "ingredients" in chef_reply.lower()

    # Verify conversation title was updated automatically
    updated_convo = client.get(f"/conversations/{convo_id}", headers=headers).json()
    assert updated_convo["title"] != "New Conversation"
    assert "Lasagna" in updated_convo["title"]
