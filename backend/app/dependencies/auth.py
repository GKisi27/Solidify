import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.PyJWTError, KeyError, ValueError):
        logger.warning("Invalid or expired access token")
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_error

    return user