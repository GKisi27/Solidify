from fastapi import APIRouter, Form, HTTPException
from app.services.auth_services import login_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        result = login_user(username, password)
        if result:
            return {
                "access_token": result["token"],
                "token_type": "bearer",
                "username": result["username"],
                "user_id": result["user_id"]
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")

    except HTTPException:
        raise 

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")