"""User Pydantic schemas"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterResponse(BaseModel):
    """Response schema for user registration"""

    id: str = Field(..., description="생성된 사용자 ID")
    email: EmailStr = Field(..., description="등록된 이메일 주소")
    created_at: datetime = Field(..., description="계정 생성 시각")


class UserResponse(BaseModel):
    """Response schema for user info"""

    id: str = Field(..., description="사용자 ID")
    email: EmailStr = Field(..., description="이메일 주소")
    status: Literal["ACTIVE", "INACTIVE", "LOCKED"] = Field(..., description="계정 상태")
    created_at: datetime = Field(..., description="계정 생성 시각")

    model_config = {"from_attributes": True}


class UserInDB(BaseModel):
    """User data in database (internal use)"""

    id: str
    email: str
    password_hash: str
    status: str
    created_at: datetime
    updated_at: datetime
    locked_until: datetime | None = None

    model_config = {"from_attributes": True}
