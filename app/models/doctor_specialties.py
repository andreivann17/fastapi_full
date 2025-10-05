# app/models/doctor_specialties.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection
from mysql.connector import IntegrityError

class DoctorSpecialtiesModel:
    # ---- helpers ----
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM doctor_specialties WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def pair_exists(self, id_doctor: int, id_specialty: int, exclude_code: Optional[str] = None) -> bool:
        """Evita duplicar la misma pareja doctor+specialty."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                if exclude_code:
                    cur.execute(
                        """
                        SELECT 1 FROM doctor_specialties
                        WHERE id_doctor=%s AND id_specialty=%s AND code<>%s
                        LIMIT 1
                        """,
                        (id_doctor, id_specialty, exclude_code),
                    )
                else:
                    cur.execute(
                        """
                        SELECT 1 FROM doctor_specialties
                        WHERE id_doctor=%s AND id_specialty=%s
                        LIMIT 1
                        """,
                        (id_doctor, id_specialty),
                    )
                return cur.fetchone() is not None
        finally:
            conn.close()

    # ---- CRUD ----
    def add_link(self, *, code: str, id_doctor: int, id_specialty: int) -> int:
        # Si no quieres bloquear duplicados, elimina este guard.
        if self.pair_exists(id_doctor, id_specialty):
            raise IntegrityError(msg="Duplicate doctor/specialty", errno=1062, sqlstate="23000")

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO doctor_specialties
                        (id_doctor, id_specialty, code, created_at, updated_at)
                    VALUES
                        (%s, %s, %s, NOW(), NULL)
                    """,
                    (id_doctor, id_specialty, code),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def update_by_code(self, *, code: str, id_doctor: Optional[int] = None, id_specialty: Optional[int] = None) -> None:
        if id_doctor is None and id_specialty is None:
            return

        # Si ambos vienen, valida duplicado con la nueva combinación
        if id_doctor is not None and id_specialty is not None:
            if self.pair_exists(id_doctor, id_specialty, exclude_code=code):
                from mysql.connector import IntegrityError as IE
                raise IE(msg="Duplicate doctor/specialty", errno=1062, sqlstate="23000")

        conn = get_connection()
        try:
            sets: List[str] = []
            params: List[Any] = []
            if id_doctor is not None:
                sets.append("id_doctor=%s"); params.append(id_doctor)
            if id_specialty is not None:
                sets.append("id_specialty=%s"); params.append(id_specialty)
            sets.append("updated_at=NOW()")

            sql = f"UPDATE doctor_specialties SET {', '.join(sets)} WHERE code=%s"
            params.append(code)
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                conn.commit()
        finally:
            conn.close()

    def delete_by_code(self, code: str) -> None:
        """Borrado físico (no hay columna active)."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("update doctor_specialties set active = 0, updated_at = Now() WHERE code=%s", (code,))
                conn.commit()
        finally:
            conn.close()

    # ---- queries ----
    def get_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        """
        Cards: id, code, id_doctor, id_specialty (búsqueda por code).
        """
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_doctor_specialties AS id, code, id_doctor, id_specialty "
                    "FROM doctor_specialties WHERE 1=1"
                )
                params: List[Any] = []
                if search:
                    base += " AND code LIKE %s"
                    params.append(f"%{search}%")
                base += " ORDER BY id_doctor_specialties DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

doctor_specialties_model = DoctorSpecialtiesModel()

def get_doctor_specialties(id_doctor_specialties: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if id_doctor_specialties:
                cur.execute(
                    """
                    SELECT id_doctor_specialties, id_doctor, id_specialty, code, created_at, updated_at
                    FROM doctor_specialties
                    WHERE id_doctor_specialties=%s
                    """,
                    (id_doctor_specialties,),
                )
            else:
                cur.execute(
                    """
                    SELECT id_doctor_specialties, id_doctor, id_specialty, code, created_at, updated_at
                    FROM doctor_specialties
                    ORDER BY id_doctor_specialties DESC
                    """
                )
            return cur.fetchall()
    finally:
        conn.close()

def get_by_code_sql(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT id_doctor_specialties, id_doctor, id_specialty, code, created_at, updated_at
                FROM doctor_specialties
                WHERE code=%s
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
