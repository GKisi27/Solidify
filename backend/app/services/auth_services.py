import logging
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas import TokenResponse

logger = logging.getLogger(__name__)


def authenticate_user(username: str, password: str, db: Session) -> User | None:
    """Returns the User if credentials are valid, otherwise None."""
    user = db.query(User).filter(User.username == username).first()

    # Always run verify_password even on missing user to prevent timing attacks
    dummy_hash = "$2b$12$invalidhashfortimingattackprevention"
    candidate_hash = user.password if user else dummy_hash

    if not verify_password(password, candidate_hash) or not user:
        logger.warning("Failed login attempt for username: %s", username)
        return None

    return user


def build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )