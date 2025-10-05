"""
clinics_roles endpoints: CRUD simple sobre (id_clinic_rol, name).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from pydantic import BaseModel
from ..deps import get_current_user

from ..models.clinics_roles import (
    clinics_roles_model,
    get_clinics_roles,
    get_role_by_id,
)

router = APIRouter(prefix="/clinics_roles", tags=["clinics_roles"])

# ------------------------- INSERT -------------------------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
async def insert_clinic(  # (mantengo el nombre de la función si ya la usas en el front)
    name: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="`name` is required")

    if clinics_roles_model.name_exists(name):
        raise HTTPException(status_code=409, detail="Role name already exists")

    new_id = clinics_roles_model.add_role(name=name)
    return {"message": "role created", "id_clinic_rol": new_id, "name": name}

# ------------------------- GET BY ID -------------------------
@router.get("/{id_clinic_rol}")
def get_role(
    id_clinic_rol: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    role = get_role_by_id(id_clinic_rol)
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    return role

# ------------------------- LIST -------------------------
@router.get("/")
def list_clinics_roles(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_clinics_roles(None)

# ------------------------- CARDS (paginado/búsqueda) -------------------------
class ClinicsRolesCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_clinics_roles_cards(
    payload: ClinicsRolesCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return clinics_roles_model.get_roles_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ------------------------- UPDATE -------------------------
@router.patch("/update", status_code=200)
async def update_clinic(
    id_clinic_rol: int = Form(...),
    name: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="`name` is required")

    if not get_role_by_id(id_clinic_rol):
        raise HTTPException(status_code=404, detail="role not found")

    clinics_roles_model.update_role(id_clinic_rol=id_clinic_rol, name=name)
    return {"message": "role updated", "id_clinic_rol": id_clinic_rol, "name": name}

# ------------------------- DELETE (hard) -------------------------
@router.delete("/delete/{id_clinic_rol}", status_code=200)
def delete_clinic(
    id_clinic_rol: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid user ID")

    if not get_role_by_id(id_clinic_rol):
        raise HTTPException(status_code=404, detail="role not found")

    clinics_roles_model.delete_role(id_clinic_rol=id_clinic_rol)
    return {"message": "role deleted", "id_clinic_rol": id_clinic_rol}
