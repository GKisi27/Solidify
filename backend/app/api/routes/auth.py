import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_token
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas import Users, RefreshRequest, TokenResponse
from app.services.auth_services import authenticate_user, build_token_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: Users, db: Session = Depends(get_db)):
    user = authenticate_user(payload.username, payload.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return build_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = int(data["sub"])
    except (jwt.ExpiredSignatureError, jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return build_token_response(user)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user_id": current_user.id, "username": current_user.username}