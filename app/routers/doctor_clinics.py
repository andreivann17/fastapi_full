# app/routers/doctor_clinics.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel
from ..deps import get_current_user
from mysql.connector import IntegrityError  # importa arriba

from ..models.doctor_clinics import (
    doctor_clinics_model,
    get_doctor_clinics,
    get_doctor_clinic_by_id_sql,
)

router = APIRouter(prefix="/doctor_clinics", tags=["doctor_clinics"])

# ---------- INSERT ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
def insert_doctor_clinic(
    id_doctor: int = Form(...),
    id_clinic: int = Form(...),
    id_clinic_rol: int = Form(...),
    start_date: str = Form(...),          # 'YYYY-MM-DD'
    end_date: Optional[str] = Form(None), # 'YYYY-MM-DD' o NULL
    notes: Optional[str] = Form(None),
    active: str = Form("1"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")


    new_id = doctor_clinics_model.add_doctor_clinic(
        id_doctor=id_doctor,
        id_clinic=id_clinic,
        id_clinic_rol=id_clinic_rol,
        start_date=start_date,
        end_date=end_date,
        notes=notes,
        active=active,
    )

    return {"message": "doctor_clinic created", "id_doctor_clinic": new_id}

# ---------- GET BY ID ----------
@router.get("/{id_doctor_clinic}")
def get_by_id(
    id_doctor_clinic: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    row = get_doctor_clinic_by_id_sql(id_doctor_clinic)
    if not row:
        raise HTTPException(status_code=404, detail="doctor_clinic not found")
    return row

# ---------- LIST ----------
@router.get("/")
def list_doctor_clinics(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_doctor_clinics(None)

# ---------- CARDS (paginado + búsqueda) ----------
class DoctorClinicsCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_cards(
    payload: DoctorClinicsCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return doctor_clinics_model.get_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

@router.patch("/update", status_code=200)
def update_doctor_clinic(
    id_doctor_clinic: int = Form(...),
    id_doctor: Optional[int] = Form(None),
    id_clinic: Optional[int] = Form(None),
    id_clinic_rol: Optional[int] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    active: Optional[int] = Form("1"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")



    try:
        doctor_clinics_model.update_doctor_clinic(
            id_doctor_clinic=id_doctor_clinic,
            id_doctor=id_doctor,
            id_clinic=id_clinic,
            id_clinic_rol=id_clinic_rol,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
            active=active,   # ← usa status, no active
        )
    except IntegrityError as e:
        # Índice único violado (uk_dc_pair)
        raise HTTPException(status_code=409, detail="Duplicate doctor/clinic/role combination") from e

    return {"message": "doctor_clinic updated", "id_doctor_clinic": id_doctor_clinic}
# ---------- DELETE (soft) ----------
@router.patch("/delete/{id_doctor_clinic}", status_code=200)
def delete_doctor_clinic(
    id_doctor_clinic: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    doctor_clinics_model.delete_doctor_clinic(id_doctor_clinic=id_doctor_clinic)
    return {"message": "doctor_clinic deleted", "id_doctor_clinic": id_doctor_clinic}
