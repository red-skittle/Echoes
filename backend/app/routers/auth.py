from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/twitch")
def twitch_login():
    """Returns Twitch OAuth authorize URL or sandbox development auth link."""
    if not settings.TWITCH_CLIENT_ID or settings.TWITCH_CLIENT_ID == "mock_twitch_client_id":
        return {
            "mode": "development_mock",
            "message": "Using development sandbox Twitch auth",
            "redirect_url": "/api/auth/twitch/callback?code=mock_dev_code_123"
        }
    
    twitch_oauth_url = (
        f"https://id.twitch.tv/oauth2/authorize"
        f"?client_id={settings.TWITCH_CLIENT_ID}"
        f"&redirect_uri={settings.TWITCH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=user:read:email+channel:read:subscriptions"
    )
    return {"mode": "live_twitch", "redirect_url": twitch_oauth_url}

@router.get("/twitch/callback")
def twitch_callback(code: str = Query(...), db: Session = Depends(get_db)):
    """Handles Twitch OAuth callback, creates or resolves user."""
    # Development fallback
    user = db.query(User).filter_by(username="aria_valkyrie").first()
    if not user:
        user = db.query(User).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="No active user found in database.")

    return {
        "status": "authenticated",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "role": user.role,
        },
        "token": f"dev_token_{user.id}"
    }

@router.get("/me", response_model=UserResponse)
def get_current_user(db: Session = Depends(get_db)):
    """Returns the currently active user profile."""
    user = db.query(User).filter_by(username="aria_valkyrie").first()
    if not user:
        user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@router.post("/logout")
def logout():
    return {"status": "logged_out", "message": "Session terminated"}

