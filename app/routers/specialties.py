# app/routers/specialties.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import os, uuid, imghdr, secrets, string, json
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel
from ..deps import get_current_user
from ..models.specialties import (
    specialties_model,
    get_specialties,
    get_specialty_by_id,
 
)
ALPHANUM = string.ascii_uppercase + string.digits
router = APIRouter(prefix="/specialties", tags=["specialties"])
def generate_code(n: int = 12) -> str:
    """Genera un code criptográficamente aleatorio."""
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))

def get_unique_code(max_tries: int = 5) -> str:
    """Genera un code que no exista en BD."""
    for _ in range(max_tries):
        code = generate_code(12)
        if not specialties_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")

# ---------- INSERT ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
def insert_specialty(
    name: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    code = get_unique_code()
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="`name` is required")
    if specialties_model.name_exists(name):
        raise HTTPException(status_code=409, detail="Specialty name already exists")

    new_id = specialties_model.add_specialty(name,code)
    return {"message": "Specialty created successfully", "code": new_id, "name": name}

# ---------- LIST ----------
@router.get("/", response_model=List[Dict[str, Any]])
def list_specialties(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return get_specialties(None)

# ---------- GET ONE ----------
@router.get("/{code}")
def get_specialty(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    row = get_specialty_by_id(code)
    if not row:
        raise HTTPException(status_code=404, detail="Specialty not found")
    return row

# ---------- CARDS (paginado/búsqueda) ----------
class SpecialtiesCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_specialties_cards(
    payload: SpecialtiesCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return specialties_model.get_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE ----------
@router.patch("/update", status_code=200)
def update_specialty(
    code: str = Form(...),
    name: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    if name is not None and not name.strip():
        raise HTTPException(status_code=422, detail="`name` cannot be empty")

    # opcional: verifica duplicado si se manda name
    if name is not None and specialties_model.name_exists(name.strip()):
        raise HTTPException(status_code=409, detail="Specialty name already exists")

    specialties_model.update_specialty(code=code, name=name.strip() if name else None)
    return {"message": "Specialty updated successfully", "code": code}

# ---------- DELETE (hard) ----------
@router.delete("/delete/{code}", status_code=200)
def delete_specialty(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")
    # opcional: podrías validar existencia primero
    specialties_model.delete_specialty(code)
    return {"message": "Specialty deleted successfully", "code": code}
