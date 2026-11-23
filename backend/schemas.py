from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator

ComplaintStatus = Literal["Pending", "Working on it", "Solved"]


# ==========================================
# 1. CATEGORY SCHEMAS
# ==========================================
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    authority_email: EmailStr


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(BaseModel):
    id: int
    name: str
    authority_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. COMPLAINT / GRIEVANCE SCHEMAS
# ==========================================
class ComplaintCreate(BaseModel):
    category_id: int = Field(..., gt=0, description="ID of the selected grievance category")
    description: str = Field(..., min_length=10, max_length=5000)

    @field_validator("description")
    @classmethod
    def strip_and_validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Complaint description cannot be empty or whitespace.")
        return cleaned


class ComplaintTrackRequest(BaseModel):
    tracking_id: str = Field(..., min_length=4, max_length=20)

    @field_validator("tracking_id")
    @classmethod
    def normalize_tracking_id(cls, value: str) -> str:
        return value.strip().upper()


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus


class ComplaintTrackResponse(BaseModel):
    tracking_id: str
    category_name: str
    status: ComplaintStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ComplaintAdminResponse(ComplaintTrackResponse):
    description: str


class ComplaintStatsResponse(BaseModel):
    total: int
    pending: int
    working: int
    solved: int


# ==========================================
# 3. ADMIN AUTH SCHEMAS
# ==========================================
class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()