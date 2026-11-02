from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the group", examples=["Goa Trip"])
    description: Optional[str] = Field(None, max_length=255, description="Optional description of the group")


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupAddMember(BaseModel):
    user_id: int = Field(..., description="ID of the user to add to the group", examples=[2])
    group_id: Optional[int] = Field(None, description="Optional group ID if specified in request body", examples=[1])


class GroupMemberResponse(BaseModel):
    id: int
    user_id: int
    name: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
