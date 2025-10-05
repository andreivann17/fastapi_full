# app/routers/patient_visits.py
from __future__ import annotations
import re, json, os, secrets, string
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Form, File
from pydantic import BaseModel
from ..deps import get_current_user

from ..models.patients_visits import (
    patient_visits_model,
    get_patient_visits,
    get_visit_by_code_sql,
)

router = APIRouter(prefix="/patient_visits", tags=["patient_visits"])

# Generación de code (A–Z, 0–9), como en los otros
ALPHANUM = string.ascii_uppercase + string.digits
def generate_code(n: int = 12) -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))

def get_unique_code(max_tries: int = 5) -> str:
    for _ in range(max_tries):
        code = generate_code(12)
        if not patient_visits_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")

# Validación de fecha/hora
def parse_dt(v: str) -> str:
    """
    Acepta 'YYYY-MM-DD HH:MM:SS' o 'YYYY-MM-DDTHH:MM:SS'
    Devuelve en formato 'YYYY-MM-DD HH:MM:SS'
    """
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    raise HTTPException(422, detail="datetime must be 'YYYY-MM-DD HH:MM:SS'")

# ---------- INSERT ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
def insert_visit(
    id_patient: int = Form(...),
    datetime_str: str = Form(...),
    id_doctor: int = Form(...),
    id_clinic: int = Form(...),
    active: int = Form(1),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    dt = parse_dt(datetime_str)
    code = get_unique_code()

    visit_id = patient_visits_model.add_visit(
        code=code,
        id_patient=id_patient,
        dt=dt,
        id_doctor=id_doctor,
        id_clinic=id_clinic,
        active=int(active),
    )

    return {
        "message": "patient_visit created successfully",
        "id_patient_visit": visit_id,
        "code": code,
    }

# ---------- GET BY CODE ----------
@router.get("/{code}")
def get_visit_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    # Permite letras/números/guión, 8–24 como en los otros códigos
    if not re.fullmatch(r"[A-Z0-9-]{8,24}", code.upper()):
        raise HTTPException(status_code=422, detail="Invalid code format")

    data = get_visit_by_code_sql(code.upper())
    if not data:
        raise HTTPException(status_code=404, detail="patient_visit not found")
    return data

# ---------- LIST ----------
@router.get("/")
def list_patient_visits(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_patient_visits(None)

# ---------- CARDS ----------
class PatientVisitsCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_cards(
    payload: PatientVisitsCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return patient_visits_model.get_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE (por code) ----------
@router.patch("/update", status_code=200)
def update_visit(
    data: str = File(...),                      # JSON con campos; debe incluir 'code'
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    try:
        payload: Dict[str, Any] = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in data")

    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=422, detail="code is required")

    # normalizar datetime si viene
    if "datetime" in payload and payload["datetime"]:
        payload["datetime"] = parse_dt(str(payload["datetime"]))

    patient_visits_model.edit_visit_by_code(payload)
    return {"message": "patient_visit updated successfully", "code": code}

# ---------- DELETE (soft) ----------
@router.patch("/delete/{code}", status_code=200)
def delete_visit(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    patient_visits_model.delete_visit(code)
    return {"message": "patient_visit deleted", "code": code}
