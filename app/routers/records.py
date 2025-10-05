"""
Record endpoints.

Defines routes for retrieving detection records and progress.
Includes endpoints for listing records, fetching detail, fetching
cards within a date range and checking progress over a week. All
operations are protected by JWT authentication.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from ..deps import get_current_user
from ..models import records as records_model

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/{detection_id}")
def get_records(
    detection_id: Optional[int],
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve detection records (optionally a single one) and lookup data."""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")
    return records_model.get_records(user_id=user_id, detection_id=detection_id)


# ------- NUEVO: body sin idPatient (y admite extra para no fallar si llega) -------
class RecordsCardsPublicRequest(BaseModel):
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    # si el frontend sigue mandando idPatient u otros campos, se ignoran
    model_config = ConfigDict(extra="allow")


@router.post("/cards")
def get_records_cards_public(
    payload: RecordsCardsPublicRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Return detection cards filtered SOLO por rango de fechas (sin filtro de paciente).
    Si el body trae `idPatient`, se ignora.
    """
    return records_model.get_records_cards_no_patient(
        start_date=payload.startDate,
        end_date=payload.endDate,
    )


# ------- Mantengo el endpoint CON paciente, pero en una ruta separada -------
class RecordsCardsRequest(BaseModel):
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    idPatient: Optional[str] = None


@router.post("/cards/by-patient")
def get_records_cards_by_patient(
    payload: RecordsCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return detection cards filtradas por paciente y fecha."""
    return records_model.get_records_cards(
        patient_id=payload.idPatient,
        start_date=payload.startDate,
        end_date=payload.endDate,
    )


class RecordDetailsRequest(BaseModel):
    code: str


@router.post("/details")
def get_record_details(
    payload: RecordDetailsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return full details for a detection code."""
    return records_model.get_record_details(payload.code)


@router.get("/check")
def get_records_details_check_today(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return cards for today (for the requesting user)."""
    # Determine current date range in UTC (00:00:00 to 23:59:59)
    today = _dt.date.today()
    start = today.strftime("%Y-%m-%d 00:00:00")
    end = today.strftime("%Y-%m-%d 23:59:59")
    user_id = current_user.get("id")
    return records_model.get_records_cards(str(user_id), start, end)


class ProgressRequest(BaseModel):
    startDate: str
    endDate: str
    idPatient: str


@router.post("/progress")
def get_records_progress(
    payload: ProgressRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return detection presence over a date range for a patient."""
    return records_model.check_week_progress(
        patient_id=payload.idPatient,
        start_date=payload.startDate,
        end_date=payload.endDate,
    )
