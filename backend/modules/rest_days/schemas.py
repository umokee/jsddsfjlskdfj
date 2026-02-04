"""
RestDay Pydantic schemas for API request/response.
"""
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class RestDayBase(BaseModel):
    date: date
    description: Optional[str] = None


class RestDayCreate(RestDayBase):
    """Schema for creating a rest day."""
    pass


class RestDayResponse(RestDayBase):
    """Schema for rest day response."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
