from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SplitDetail(BaseModel):
    user_id: int = Field(..., description="User ID involved in the split")
    amount: Decimal = Field(..., gt=0, description="Exact amount owed by this user")

    @field_validator("amount")
    @classmethod
    def validate_two_decimal_places(cls, v: Decimal) -> Decimal:
        return round(v, 2)


class ExpenseCreate(BaseModel):
    group_id: int = Field(..., description="ID of the group the expense belongs to", examples=[1])
    paid_by: int = Field(..., description="ID of the user who paid for the expense", examples=[1])
    amount: Decimal = Field(..., gt=0, description="Total amount of the expense, must be > 0", examples=[1200.0])
    description: str = Field(..., min_length=1, max_length=255, description="Description of the expense", examples=["Dinner"])
    split_type: Optional[str] = Field("EQUAL", description="Split type: 'EQUAL' or 'EXACT'")
    splits: Optional[List[SplitDetail]] = Field(None, description="Optional custom splits if split_type is 'EXACT'")

    @field_validator("amount")
    @classmethod
    def validate_two_decimal_places(cls, v: Decimal) -> Decimal:
        return round(v, 2)


class ExpenseSplitResponse(BaseModel):
    user_id: int
    user_name: str
    amount_owed: Decimal

    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    paid_by: str  # User's name as specified in the PDF assignment
    paid_by_id: int
    group_id: int
    split_type: str
    created_at: datetime
    splits: List[ExpenseSplitResponse] = []

    model_config = ConfigDict(from_attributes=True)
