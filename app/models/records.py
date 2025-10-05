# app/models/doctors.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection

class DoctorsModel:
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM doctors WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def get_current_img_by_code(self, code: str) -> str:
        """Devuelve la ruta img actual para ese code (o cadena vacía)."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT img FROM doctors WHERE code=%s", (code,))
                row = cur.fetchone()
                if not row:
                    raise ValueError("doctor not found")
                (img,) = row
                return img or ""
        finally:
            conn.close()

    def add_doctor(
        self,
        *,
        code: str,
        first_name: str,
        last_name: str,
        email: Optional[str],
        id_gender: int,
        birth_date: str,            # YYYY-MM-DD
        city: int,
        state: int,
        country: int,
        img: str,                   # ruta pública o ""
        active: int,
        cedula: Optional[str],
        created_by: int,            # id_user
    ) -> int:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO doctors
                        (first_name, last_name, email, id_gender, birth_date,
                         code, active, city, state, country, img,
                         date, time, id_user, created_at, updated_at, cedula)
                    VALUES
                        (%s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s,
                         CURDATE(), CURTIME(), %s, NOW(), NULL, %s)
                    """,
                    (
                        first_name, last_name, email, id_gender, birth_date,
                        code, active, city, state, country, img,
                        created_by, cedula,
                    ),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def delete_doctor(self, code: str, user_id: int) -> None:
        """Soft delete -> active=0 + date/time + updated_at + auditoría mínima."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE doctors
                       SET active = 0,
                           date = CURDATE(),
                           time = CURTIME(),
                           updated_at = NOW(),
                           id_user = %s
                     WHERE code = %s
                    """,
                    (user_id, code),
                )
                conn.commit()
        finally:
            conn.close()

    def get_doctors_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        """Listado paginado para cards (busca por nombre y email)."""
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_doctor AS id, code, "
                    "CONCAT(first_name,' ',last_name) AS name, email "
                    "FROM doctors WHERE active = 1"
                )
                params: List[Any] = []
                if search:
                    base += " AND (first_name LIKE %s OR last_name LIKE %s OR email LIKE %s)"
                    like = f"%{search}%"
                    params.extend([like, like, like])
                base += " ORDER BY id_doctor DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

doctors_model = DoctorsModel()

def get_doctors(doctor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Listado o detalle con columnas reales."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if doctor_id:
                cur.execute(
                    """
                    SELECT
                        id_doctor, first_name, last_name, email, id_gender,
                        birth_date, code, active, city, state, country, img,
                        date, time, id_user, created_at, updated_at, cedula
                    FROM doctors
                    WHERE id_doctor = %s
                    """,
                    (doctor_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        id_doctor, first_name, last_name, email, id_gender,
                        birth_date, code, active, city, state, country, img,
                        date, time, id_user, created_at, updated_at, cedula
                    FROM doctors
                    WHERE active = 1
                    ORDER BY id_doctor DESC
                    """
                )
            return cur.fetchall()
    finally:
        conn.close()

def get_doctor_by_code_sql(code: str) -> Optional[Dict[str, Any]]:
    """Devuelve un dict por 'code' o None si no existe."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                    id_doctor, first_name, last_name, email, id_gender,
                    birth_date, code, active, city, state, country, img,
                    date, time, id_user, created_at, updated_at, cedula
                FROM doctors
                WHERE code = %s
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def edit_doctor_by_code(data: Dict[str, Any], user_id: int) -> None:
    """
    Actualiza doctor usando code como identificador.
    Acepta: firstName, lastName, email, idGender, birthDate, img,
            city, state, country, active, cedula, code
    """
    conn = get_connection()
    try:
        sets: List[str] = []
        params: List[Any] = []

        if "firstName" in data:  sets.append("first_name = %s"); params.append(data["firstName"])
        if "lastName"  in data:  sets.append("last_name  = %s"); params.append(data["lastName"])
        if "email"     in data:  sets.append("email      = %s"); params.append(data["email"])
        if "idGender"  in data:  sets.append("id_gender  = %s"); params.append(data["idGender"])
        if "birthDate" in data:  sets.append("birth_date = %s"); params.append(data["birthDate"])
        if "img"       in data:  sets.append("img        = %s"); params.append(data["img"])
        if "city"      in data:  sets.append("city       = %s"); params.append(data["city"])
        if "state"     in data:  sets.append("state      = %s"); params.append(data["state"])
        if "country"   in data:  sets.append("country    = %s"); params.append(data["country"])
        if "active"    in data:  sets.append("active     = %s"); params.append(data["active"])
        if "cedula"    in data:  sets.append("cedula     = %s"); params.append(data["cedula"])

        # auditoría mínima
        sets.append("date = CURDATE()")
        sets.append("time = CURTIME()")
        sets.append("updated_at = NOW()")
        sets.append("id_user = %s")
        params.append(user_id)

        if len(sets) == 4:  # sólo auditoría -> nada que actualizar
            return

        sql = f"UPDATE doctors SET {', '.join(sets)} WHERE code = %s"
        params.append(data["code"])

        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            conn.commit()
    finally:
        conn.close()
