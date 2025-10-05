# app/routers/doctors.py
from __future__ import annotations
import os, imghdr, secrets, string, json, re
from typing import Any, Dict, List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from ..deps import get_current_user
from ..models.doctors import (
    doctors_model,
    get_doctors,
    get_doctor_by_code_sql,
    edit_doctor_by_code,
)

router = APIRouter(prefix="/doctors", tags=["doctors"])

EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
UPLOAD_DIR = "uploads/doctors"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALPHANUM = string.ascii_uppercase + string.digits
def generate_code(n: int = 12) -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))

def get_unique_code(max_tries: int = 5) -> str:
    for _ in range(max_tries):
        code = generate_code(12)
        if not doctors_model.code_exists(code):
            return code
    raise HTTPException(500, "Could not generate unique code")

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

# ---------- INSERT ----------
@router.post("/insert", status_code=status.HTTP_201_CREATED)
async def insert_doctor(
    firstName: str = Form(...),
    lastName: str = Form(...),
    email: Optional[str] = Form(None),
    idGender: int = Form(...),
    birthDate: str = Form(...),
    city: int = Form(...),
    state: int = Form(...),
    country: int = Form(...),
    active: int = Form(1),
    cedula: Optional[str] = Form(None),
    img: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Crea un doctor usando solo columnas reales de `doctors`."""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user ID")

    # validar nombre y mail
    first = firstName.strip()
    last  = lastName.strip()
    if not first or not last:
        raise HTTPException(422, detail="firstName and lastName are required")

    if email:
        e = email.strip()
        if not EMAIL_RE.match(e):
            raise HTTPException(422, detail="Invalid email")
        email = e

    bdate = parse_birthdate(birthDate).isoformat()
    code = get_unique_code()

    # Manejo de imagen (opcional)
    img_rel_path = ""
    if img is not None:
        if img.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(415, detail="Only JPEG/PNG/WebP are allowed")

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
            raise HTTPException(400, detail="Invalid image file")

        img_rel_path = f"/uploads/doctors/{filename}"

    # Insert
    try:
        doctors_model.add_doctor(
            code=code,
            first_name=first,
            last_name=last,
            email=email,
            id_gender=idGender,
            birth_date=bdate,
            city=city,
            state=state,
            country=country,
            img=img_rel_path,
            active=int(active),
            cedula=(cedula or None),
            created_by=user_id,
        )
    except Exception:
        # limpieza si falló
        if img_rel_path:
            try:
                os.remove(os.path.join(UPLOAD_DIR, os.path.basename(img_rel_path)))
            except Exception:
                pass
        raise

    return {
        "message": "doctor created successfully",
        "code": code,
        "img": img_rel_path,
    }

# ---------- GET BY CODE ----------
@router.get("/{code}")
def get_doctor_by_code(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not re.fullmatch(r"[A-Z0-9-]{8,24}", code.upper()):
        raise HTTPException(422, detail="Invalid code format")

    data = get_doctor_by_code_sql(code.upper())
    if not data:
        raise HTTPException(404, detail="doctor not found")
    return data

# ---------- LIST ----------
@router.get("/")
def list_doctors(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return get_doctors(None)

# ---------- CARDS ----------
class DoctorsCardsRequest(BaseModel):
    limit: int = 10
    search: Optional[str] = ""
    offset: int = 0

@router.post("/cards")
def get_doctors_cards(
    payload: DoctorsCardsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return doctors_model.get_doctors_cards(
        limit=payload.limit, search=payload.search or "", offset=payload.offset
    )

# ---------- UPDATE por CODE ----------
@router.patch("/update", status_code=200)
async def update_doctor(
    data: str = File(...),                # JSON con campos; debe incluir 'code'
    img: Optional[UploadFile] = File(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(401, detail="Invalid user ID")

    try:
        payload: Dict[str, Any] = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(400, detail="Invalid JSON in data")

    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(422, detail="code is required")

    # validar email si viene
    if "email" in payload and payload["email"]:
        if not EMAIL_RE.match(str(payload["email"]).strip()):
            raise HTTPException(422, detail="Invalid email")

    # normalizar fecha si viene
    if payload.get("birthDate"):
        payload["birthDate"] = parse_birthdate(payload["birthDate"]).isoformat()

    # obtener img actual por code
    current_img = doctors_model.get_current_img_by_code(code)
    new_img_path = current_img or ""
    wrote_new_file = False

    if img is not None:
        if img.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(415, detail="Only JPEG/PNG/WebP are allowed")

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
            raise HTTPException(400, detail="Invalid image file")

        # si cambió el nombre, borra la anterior
        if current_img:
            old_rel = current_img[1:] if current_img.startswith("/") else current_img
            old_abs = os.path.join(os.getcwd(), old_rel)
            if os.path.exists(old_abs) and os.path.abspath(old_abs) != os.path.abspath(abs_path):
                try:
                    os.remove(old_abs)
                except OSError:
                    pass

        new_img_path = f"/uploads/doctors/{filename}"

    payload["img"] = new_img_path
    payload["code"] = code  # asegurar

    try:
        edit_doctor_by_code(payload, user_id)
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

    return {"message": "doctor updated successfully", "img": payload["img"]}

# ---------- DELETE (soft) ----------
@router.patch("/delete/{code}", status_code=200)
def delete_doctor(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(401, detail="Invalid user ID")
    doctors_model.delete_doctor(code, user_id)
    return {"message": "doctor successfully deleted", "code": code}
