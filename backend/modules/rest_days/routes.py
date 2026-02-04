"""
RestDay HTTP routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.core.security import verify_api_key
from backend.core.exceptions import NotFoundError
from .service import RestDayService
from .schemas import RestDayCreate, RestDayResponse

router = APIRouter(prefix="/api/rest-days", tags=["rest-days"])


@router.get("", response_model=List[RestDayResponse])
def get_rest_days(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get all rest days."""
    service = RestDayService(db)
    return service.get_all()


@router.post("", response_model=RestDayResponse)
def create_rest_day(
    rest_day_data: RestDayCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Create a new rest day."""
    service = RestDayService(db)
    return service.create(rest_day_data)


@router.delete("/{rest_day_id}")
def delete_rest_day(
    rest_day_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Delete a rest day."""
    service = RestDayService(db)
    try:
        service.delete(rest_day_id)
        return {"message": "Rest day deleted successfully"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Rest day {rest_day_id} not found")
