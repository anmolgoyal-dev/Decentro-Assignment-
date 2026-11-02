from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Full name of the user", examples=["Mohit"])
    email: Optional[str] = Field(None, max_length=255, description="Optional unique email address", examples=["mohit@example.com"])


class UserResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
