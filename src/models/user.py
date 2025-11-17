"""
User authentication models
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator, EmailStr


class User(BaseModel):
    """User account model"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: Optional[EmailStr] = Field(None, description="User email (optional)")
    password_hash: str = Field(..., description="Hashed password")

    # User metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = Field(True, description="Account active status")

    # Notification settings
    pushover_key: Optional[str] = Field(None, description="Pushover user key for notifications")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")

    # Additional info
    full_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, description="User timezone")

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores and hyphens')
        return v.lower()  # Store usernames in lowercase

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserCreate(BaseModel):
    """Model for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, description="Plain password (will be hashed)")
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    """Model for user login"""
    username: str
    password: str


class Session(BaseModel):
    """User session model"""
    session_id: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    username: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if session is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class UserUpdate(BaseModel):
    """Model for updating user profile"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    pushover_key: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    timezone: Optional[str] = None
