"""
arquitecture endpoints.

Defines API routes for creating, reading, updating and deleting
arquitectures. Authentication is enforced on sensitive operations using
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
from ..models.arquitectures import arquitectures_model, edit_arquitecture_by_code, get_arquitectures,get_arquitecture_by_code_sql  # <-- NUEVO import
from dateutil.relativedelta import relativedelta
from ..deps import get_current_user
from ..db import get_connection
router = APIRouter(prefix="/arquitectures", tags=["arquitectures"])

EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")

# Carpeta pública montada en main.py con:
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
UPLOAD_DIR = "uploads/arquitectures"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Código alfanumérico (A–Z, 0–9)
ALPHANUM = string.ascii_uppercase + string.digits

def _parse_to_month_start(s: str) -> date:
    """
    Acepta 'YYYY', 'YYYY-MM' o 'YYYY-MM-DD' y regresa el primer día de ese mes.
    """
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            d = datetime.strptime(s, fmt).date()
            return d.replace(day=1)
        except ValueError:
            continue
    raise HTTPException(422, detail="startDate/endDate must be YYYY, YYYY-MM, or YYYY-MM-DD")

def _month_range_inclusive(a: date, b: date) -> List[date]:
    """
    Lista de primeros de mes desde a..b (ambos inclusive en meses).
    """
    if a > b:
        a, b = b, a
    months = []
    cur = a.replace(day=1)
    end = b.replace(day=1)
    while cur <= end:
        months.append(cur)
        cur = (cur + relativedelta(months=1))
    return months
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
        if not arquitectures_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")


# ---------- INSERT (multipart/form-data) ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
async def insert_arquitecture(
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: Optional[str] = Form(None),   # opcional (hazlo obligatorio si quieres)
    idGender: int = Form(...),
    birthDate: str = Form(...),
    city: int = Form(...),
    state: int = Form(...),
    country: int = Form(...),
    img: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Create a new arquitecture (multipart/form-data). Guarda email si se envía.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID")

    # 1) Normalizar fecha
    bdate = parse_birthdate(birthDate).isoformat()

    # 2) Generar code único (USAR FUNCIÓN LOCAL; NO IMPORTAR MÓDULOS INEXISTENTES)
    code = get_unique_code()

    # 3) Validar email si viene
    if email and not EMAIL_RE.match(email.strip()):
        raise HTTPException(status_code=422, detail="Invalid email")

    # 4) Manejo de imagen (opcional)
    img_rel_path = ""
    img_ext = ".jpg"
    img_bytes: Optional[bytes] = None

    if img is not None:
        if img.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP are allowed")

        orig_ext = (os.path.splitext(img.filename or "")[1].lower() or ".jpg")
        if orig_ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            orig_ext = ".jpg"
        img_ext = orig_ext

        img_bytes = await img.read()
        filename = f"{code}{img_ext}"
        abs_path = os.path.join(UPLOAD_DIR, filename)

        with open(abs_path, "wb") as f:
            f.write(img_bytes)

        if imghdr.what(abs_path) not in {"jpeg", "png", "webp"}:
            os.remove(abs_path)
            raise HTTPException(status_code=400, detail="Invalid image file")

        img_rel_path = f"/uploads/arquitectures/{filename}"

    # 5) Insert
    try:
        arquitectures_model.add_arquitecture(
            code=code,
            first_name=firstName.strip(),
            last_name=lastName.strip(),
            email=(email or "").strip(),
            gender_id=idGender,
            birth_date=bdate,
            city=city,
            state=state,
            country=country,
            img=img_rel_path,
            created_by=user_id,
        )
    except Exception:
        # limpia archivo si falló
        if img_bytes is not None:
            file_path = os.path.join(UPLOAD_DIR, f"{code}{img_ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
        raise

    # 6) Respuesta
    return {
        "message": "The arquitecture information was created successfully",
        "code": code,
        "img": img_rel_path,
    }

@router.get("/by-id/{arquitecture_id}", deprecated=True)
def get_arquitecture_by_id_legacy(
    arquitecture_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    # Si aún necesitas el viejo flujo un tiempo:
    return get_arquitectures(arquitecture_id)

@router.get("/{code}")
def get_arquitecture_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve a single arquitecture along with lookup data, by arquitecture CODE.
    Path param: `code` (string alfanumérico, p.ej. 'AB12C3D4E5F6').
    """
    # Validación rápida: 8–24 alfanumérico (ajusta si usas largo fijo 12)
    if not re.fullmatch(r"[A-Z0-9]{8,24}", code.upper()):
        raise HTTPException(status_code=422, detail="Invalid code format")

    data = get_arquitecture_by_code_sql(code.upper())
    if not data:
        raise HTTPException(status_code=404, detail="arquitecture not found")

    return data


@router.get("/")
def list_arquitectures(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all arquitectures with lookup data."""
    return get_arquitectures(None)


class arquitecturesCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0


@router.post("/cards")
def get_arquitectures_cards(
    payload: arquitecturesCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return a paginated list of arquitecture cards."""
    return arquitectures_model.get_arquitectures_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE por CODE (multipart/form-data) ----------
@router.patch("/update", status_code=200)
async def update_arquitecture(
    data: str = File(...),                      # JSON string con campos, incluyendo 'code'
    img: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update arquitecture identified by 'code'.
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

    # validar email si viene
    if "email" in payload and payload["email"]:
        if not EMAIL_RE.match(str(payload["email"]).strip()):
            raise HTTPException(status_code=422, detail="Invalid email")

    # normalizar fecha si viene
    if payload.get("birthDate"):
        payload["birthDate"] = parse_birthdate(payload["birthDate"]).isoformat()

    # obtener img actual por code
    current_img = arquitectures_model.get_current_img_by_code(code)  # <-- NUEVO helper en modelo

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

        new_img_path = f"/uploads/arquitectures/{filename}"

    payload["img"] = new_img_path
    payload["code"] = code  # asegurar

    try:
        edit_arquitecture_by_code(payload, user_id)  # <-- UPDATE usando WHERE code = %s
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

    return {"message": "arquitecture updated successfully", "img": payload["img"]}
@router.patch("/delete/{code}", status_code=200)
def delete_arquitecture(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Soft delete a arquitecture."""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID")
    arquitectures_model.delete_arquitecture(code, user_id)
    return {"message": "arquitecture successfully deleted", "code": code}
