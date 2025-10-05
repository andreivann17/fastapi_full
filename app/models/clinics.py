# app/models/clinics.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection

class clinicsModel:
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM clinics WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def get_current_img_by_code(self, code: str) -> str:
        """
        La tabla no tiene columna 'img'. Conservamos la función,
        validamos que exista el code y devolvemos "".
        """
        if not self.code_exists(code):
            raise ValueError("clinic not found")
        return ""

    def add_clinic(
        self,
        *,
        code: str,
        name: str,
        email: Optional[str] = None,
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        phone: Optional[str] = None,
        active: str = "1",
    ) -> None:
        """
        Inserta SOLO columnas reales: code, name, address_line1/2, city, state,
        country, zip_code, phone, email, active, created_at, updated_at.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clinics
                        (code, name, address_line1, address_line2,
                         city, state, country, zip_code, phone,
                         email, active, created_at, updated_at)
                    VALUES
                        (%s,   %s,   %s,            %s,
                         %s,   %s,   %s,      %s,      %s,
                         %s,   %s,     NOW(),   NULL)
                    """,
                    (
                        code,
                        name,
                        address_line1,
                        address_line2,
                        city,
                        state,
                        country,
                        zip_code,
                        phone,
                        email,
                        active,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def delete_clinic(self, code: str, user_id: int) -> None:
        """
        Borrado lógico: active='inactive', updated_at=NOW().
        (user_id no existe en la tabla; se ignora)
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE clinics
                       SET active = 0,
                           updated_at = NOW()
                     WHERE code = %s
                    """,
                    (code,),
                )
                conn.commit()
        finally:
            conn.close()

    def get_clinics_cards(
        self,
        limit: int, search: str = "", offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Cards: id, code, name, email. Solo active='active'."""
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_clinic AS id, code, name, email "
                    "FROM clinics WHERE active = 1"
                )
                params: List[Any] = []
                if search:
                    base += " AND (name LIKE %s OR email LIKE %s OR code LIKE %s)"
                    like = f"%{search}%"
                    params.extend([like, like, like])
                base += " ORDER BY id_clinic DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

clinics_model = clinicsModel()

def get_gender_list() -> List[Dict[str, Any]]:
    """Sin catálogos/relaciones para clinics."""
    return []

def get_blood_type_list() -> List[Dict[str, Any]]:
    """Sin catálogos/relaciones para clinics."""
    return []

def get_clinics(clinic_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Listado/detalle con columnas reales."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if clinic_id:
                cur.execute(
                    """
                    SELECT
                        p.id_clinic,
                        p.code,
                        p.name,
                        p.address_line1,
                        p.address_line2,
                        p.city,
                        p.state,
                        p.country,
                        p.zip_code,
                        p.phone,
                        p.email,
                        p.active,
                        p.created_at,
                        p.updated_at
                    FROM clinics p
                    WHERE p.id_clinic = %s
                    """,
                    (clinic_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        p.id_clinic,
                        p.code,
                        p.name,
                        p.address_line1,
                        p.address_line2,
                        p.city,
                        p.state,
                        p.country,
                        p.zip_code,
                        p.phone,
                        p.email,
                        p.active,
                        p.created_at,
                        p.updated_at
                    FROM clinics p
                    WHERE p.active = 1
                    ORDER BY p.id_clinic DESC
                    """
                )
            clinics = cur.fetchall()
        return clinics
    finally:
        conn.close()

def get_clinic_by_code_sql(code: str) -> Optional[Dict[str, Any]]:
    """Detalle por code con columnas reales."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT 
                    id_clinic,
                    code,
                    name,
                    address_line1,
                    address_line2,
                    city,
                    state,
                    country,
                    zip_code,
                    phone,
                    email,
                    active,
                    created_at,
                    updated_at
                FROM clinics 
                WHERE code = %s
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def edit_clinic_by_code(data: Dict[str, Any], user_id: int) -> None:
    """
    Update por 'code' con columnas reales.
    Acepta 'name' directamente o arma nombre con firstName/lastName si vienen.
    Ignora campos inexistentes.
    """
    name = data.get("name")
    if not name:
        fn = (data.get("firstName") or "").strip()
        ln = (data.get("lastName") or "").strip()
        name = f"{fn} {ln}".strip() or None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE clinics
                   SET name          = %s,
                       email         = %s,
                       city          = %s,
                       state         = %s,
                       country       = %s,
                       address_line1 = %s,
                       address_line2 = %s,
                       zip_code      = %s,
                       phone         = %s,
                       active        = COALESCE(%s, 1),
                       updated_at    = NOW()
                 WHERE code = %s
                """,
                (
                    name,
                    data.get("email"),
                    data.get("city"),
                    data.get("state"),
                    data.get("country"),
                    data.get("address_line1"),
                    data.get("address_line2"),
                    data.get("zip_code"),
                    data.get("phone"),
                    data.get("active"),   # 'active' o 'inactive' si lo envías
                    data.get("code"),
                ),
            )
            conn.commit()
    finally:
        conn.close()
