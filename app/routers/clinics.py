"""
clinic endpoints.

Defines API routes for creating, reading, updating and deleting
clinics. Authentication is enforced on sensitive operations using
the ``get_current_user`` dependency.
"""

from __future__ import annotations
import uuid
import imghdr
from typing import Any, Dict, List, Optional
import os, uuid, imghdr, secrets, string, json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status,Form,Query
from pydantic import BaseModel, field_validator
from datetime import date, datetime
from mysql.connector import Error as MySQLError,IntegrityError, DataError as MySQLDataError
import re
from ..models.clinics import clinics_model, edit_clinic_by_code, get_clinics,get_clinic_by_code_sql  # <-- NUEVO import
from dateutil.relativedelta import relativedelta
from ..deps import get_current_user
from ..db import get_connection
router = APIRouter(prefix="/clinics", tags=["clinics"])

EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")

# Carpeta pública montada en main.py con:
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
UPLOAD_DIR = "uploads/clinics"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Código alfanumérico (A–Z, 0–9)
ALPHANUM = string.ascii_uppercase + string.digits


def parse_birthdate(v: str) -> date:
    fmts = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y", "%m-%d-%Y")
    for fmt in fmts:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise HTTPException(
        422,
        detail="birthDate must be one of: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, DD-MM-YYYY, MM-DD-YYYY",
    )

def generate_code(n: int = 12) -> str:
    """Genera un code criptográficamente aleatorio."""
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))

def get_unique_code(max_tries: int = 5) -> str:
    """Genera un code que no exista en BD."""
    for _ in range(max_tries):
        code = generate_code(12)
        if not clinics_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")


# ---------- INSERT (multipart/form-data) ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
async def insert_clinic(
    name: str = Form(...),
    email: Optional[str] = Form(None),
    address_line1: Optional[str] = Form(None),
    address_line2: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    zip_code: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    active: int = Form("1"),               # 'active' | 'inactive'
    img: Optional[UploadFile] = File(None),         # opcional: SÓLO filesystem (DB no tiene 'img')
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Crea una clínica usando ÚNICAMENTE las columnas reales de la tabla `clinics`.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID")

    # Validaciones mínimas
    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="`name` is required")

    if email:
        e = email.strip()
        if not EMAIL_RE.match(e):
            raise HTTPException(status_code=422, detail="Invalid email")
        email = e

    # Generar code (p.ej. CLIN-001, CLIN-002, ...)
    code = get_unique_code()

    # Guardado opcional de imagen en disco (NO en DB)
    img_rel_path = ""
    if img is not None:
        if img.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP are allowed")

        ext = (os.path.splitext(img.filename or "")[1].lower() or ".jpg")
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"
        filename = f"{code}{ext}"
        abs_path = os.path.join(UPLOAD_DIR, filename)

        raw = await img.read()
        with open(abs_path, "wb") as f:
            f.write(raw)

        if imghdr.what(abs_path) not in {"jpeg", "png", "webp"}:
            os.remove(abs_path)
            raise HTTPException(status_code=400, detail="Invalid image file")

        img_rel_path = f"/uploads/clinics/{filename}"

    # Insert SOLO con columnas reales
    try:
        clinics_model.add_clinic(
            code=code,
            name=name,
            email=email or None,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            country=country,
            zip_code=zip_code,
            phone=phone,
            active=active,
        )
    except Exception:
        # limpia archivo si falló
        if img_rel_path:
            try:
                os.remove(os.path.join(UPLOAD_DIR, os.path.basename(img_rel_path)))
            except Exception:
                pass
        raise

    return {
        "message": "The clinic information was created successfully",
        "code": code,
        "name": name,
        "email": email,
        "img": img_rel_path,  # solo para UI; NO está en DB
    }


@router.get("/by-id/{clinic_id}", deprecated=True)
def get_clinic_by_id_legacy(
    clinic_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    # Si aún necesitas el viejo flujo un tiempo:
    return get_clinics(clinic_id)

@router.get("/{code}")
def get_clinic_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve a single clinic along with lookup data, by clinic CODE.
    Path param: `code` (string alfanumérico, p.ej. 'AB12C3D4E5F6').
    """
    # Validación rápida: 8–24 alfanumérico (ajusta si usas largo fijo 12)
    if not re.fullmatch(r"[A-Z0-9-]{8,24}", code.upper()):
        raise HTTPException(status_code=422, detail="Invalid code format")


    data = get_clinic_by_code_sql(code.upper())
    if not data:
        raise HTTPException(status_code=404, detail="clinic not found")

    return data


@router.get("/")
def list_clinics(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_clinics(None)   # ya devuelve List[Dict]



class clinicsCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0


@router.post("/cards")
def get_clinics_cards(
    payload: clinicsCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return a paginated list of clinic cards."""
    return clinics_model.get_clinics_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE por CODE (multipart/form-data) ----------
@router.patch("/update", status_code=200)
async def update_clinic(
    data: str = File(...),                      # JSON string con campos, incluyendo 'code'
    img: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update clinic identified by 'code'.
      - data: JSON string con campos (debe incluir 'code')
      - img: archivo opcional (JPEG/PNG/WebP). Si viene, sustituye la imagen.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")

    try:
        payload: Dict[str, Any] = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in data field")

    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=422, detail="code is required")

    # obtener img actual por code
    current_img = clinics_model.get_current_img_by_code(code)  # <-- NUEVO helper en modelo

    # Manejo de imagen (opcional)
    new_img_path = current_img or ""
    wrote_new_file = False

    if img is not None:
        if img.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP are allowed")

        ext = (os.path.splitext(img.filename or "")[1].lower() or ".jpg")
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"

        filename = f"{code}{ext}"
        abs_path = os.path.join(UPLOAD_DIR, filename)
        bytes_ = await img.read()

        with open(abs_path, "wb") as f:
            f.write(bytes_)
        wrote_new_file = True

        if imghdr.what(abs_path) not in {"jpeg", "png", "webp"}:
            os.remove(abs_path)
            raise HTTPException(status_code=400, detail="Invalid image file")

        # borrar imagen anterior si el nombre cambió
        if current_img:
            old_rel = current_img[1:] if current_img.startswith("/") else current_img
            old_abs = os.path.join(os.getcwd(), old_rel)
            if os.path.exists(old_abs) and os.path.abspath(old_abs) != os.path.abspath(abs_path):
                try:
                    os.remove(old_abs)
                except OSError:
                    pass

        new_img_path = f"/uploads/clinics/{filename}"

    payload["img"] = new_img_path
    payload["code"] = code  # asegurar

    try:
        edit_clinic_by_code(payload, user_id)  # <-- UPDATE usando WHERE code = %s
    except Exception:
        if wrote_new_file and new_img_path:
            try:
                rel = new_img_path[1:] if new_img_path.startswith("/") else new_img_path
                abs_cleanup = os.path.join(os.getcwd(), rel)
                if os.path.exists(abs_cleanup):
                    os.remove(abs_cleanup)
            except OSError:
                pass
        raise

    return {"message": "clinic updated successfully", "img": payload["img"]}
@router.patch("/delete/{code}", status_code=200)
def delete_clinic(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Soft delete a clinic."""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")
    clinics_model.delete_clinic(code, user_id)
    return {"message": "clinic successfully deleted", "code": code}
