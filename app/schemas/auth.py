from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
    role_label: str
    expires_at: datetime


class UserProfile(BaseModel):
    username: str
    full_name: str
    role: str
    role_label: str
    allowed_departments: list[str]
