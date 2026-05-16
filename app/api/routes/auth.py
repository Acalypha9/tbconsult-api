from fastapi import APIRouter
from pydantic import BaseModel
from app.core.security import create_access_token

router = APIRouter()

class TokenRequest(BaseModel):
    user_id: str

@router.post("/token")
async def login_for_access_token(request: TokenRequest):
    """
    Simple auth endpoint for development/testing.
    """
    access_token = create_access_token(data={"user_id": request.user_id})
    return {"access_token": access_token, "token_type": "bearer"}
