from pydantic import BaseModel, EmailStr

from app.models.admin_user import AdminRole
from app.schemas.auth import TokenResponse

__all__ = ["AdminLoginRequest", "AdminTokenResponse", "AdminUserOut"]

AdminTokenResponse = TokenResponse


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminUserOut(BaseModel):
    id: str
    email: EmailStr
    role: AdminRole
    is_active: bool

    model_config = {"from_attributes": True}
