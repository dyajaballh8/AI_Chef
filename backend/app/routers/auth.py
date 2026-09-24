from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import UserRegister, UserLogin, Token, UserOut
from ..auth import get_password_hash, verify_password, create_access_token
from ..dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.
    - Validates email, password length, and unique username/email.
    - Hashes password securely.
    - Returns a JWT token to log the user in immediately.
    """
    clean_username = user_in.username.strip()
    clean_email = user_in.email.strip().lower()

    # Check existing email
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Check existing username
    if db.query(User).filter(User.username.ilike(clean_username)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is already taken. Please choose another."
        )

    # Hash password and persist
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        username=clean_username,
        email=clean_email,
        hashed_password=hashed_pwd
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user by username or email and password.
    Returns a signed JWT access token.
    """
    login_id = credentials.login.strip().lower()

    # Find user by email or username
    user = db.query(User).filter(
        (User.email == login_id) | (User.username.ilike(login_id))
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user
