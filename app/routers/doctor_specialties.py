# app/routers/doctor_specialties.py
from __future__ import annotations
import secrets, string, re, json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form, File
from pydantic import BaseModel
from mysql.connector import IntegrityError

from ..deps import get_current_user
from ..models.doctor_specialties import (
    doctor_specialties_model,
    get_doctor_specialties,
    get_by_code_sql,
)

router = APIRouter(prefix="/doctor_specialties", tags=["doctor_specialties"])

# ---- code generator ----
ALPHANUM = string.ascii_uppercase + string.digits
def generate_code(n: int = 12) -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))

def get_unique_code(max_tries: int = 5) -> str:
    for _ in range(max_tries):
        code = generate_code(12)
        if not doctor_specialties_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")

# ---------- INSERT ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
def insert_link(
    id_doctor: int = Form(...),
    id_specialty: int = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    code = get_unique_code()
    try:
        new_id = doctor_specialties_model.add_link(
            code=code,
            id_doctor=id_doctor,
            id_specialty=id_specialty,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate doctor/specialty")

    return {"message": "link created", "id_doctor_specialties": new_id, "code": code}

# ---------- GET BY CODE ----------
@router.get("/{code}")
def get_link_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not re.fullmatch(r"[A-Z0-9-]{8,24}", code.upper()):
        raise HTTPException(status_code=422, detail="Invalid code format")

    data = get_by_code_sql(code.upper())
    if not data:
        raise HTTPException(status_code=404, detail="link not found")
    return data

# ---------- LIST ----------
@router.get("/")
def list_links(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_doctor_specialties(None)

# ---------- CARDS ----------
class DS_CardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_cards(
    payload: DS_CardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return doctor_specialties_model.get_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE (por code) ----------
@router.patch("/update", status_code=200)
def update_link(
    data: str = File(...),  # JSON con { code, id_doctor?, id_specialty? }
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    try:
        payload: Dict[str, Any] = json.loads(data)
    except Exception:
        raise HTTPException(400, detail="Invalid JSON in data")

    code = (payload.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(422, detail="code is required")

    try:
        doctor_specialties_model.update_by_code(
            code=code,
            id_doctor=payload.get("id_doctor"),
            id_specialty=payload.get("id_specialty"),
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate doctor/specialty")

    return {"message": "link updated", "code": code}

# ---------- DELETE (hard) ----------
@router.delete("/delete/{code}", status_code=200)
def delete_link(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    doctor_specialties_model.delete_by_code(code.upper())
    return {"message": "link deleted", "code": code.upper()}
