# app/models/doctor_clinics.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection
from mysql.connector import IntegrityError  # importa arriba

class DoctorClinicsModel:
    def add_doctor_clinic(
        self,
        *,
        id_doctor: int,
        id_clinic: int,
        id_clinic_rol: int,
        start_date: str,
        end_date: Optional[str] = None,
        notes: Optional[str] = None,
        active: str = "1",
    ) -> int:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO doctor_clinics
                        (start_date, end_date, notes,
                         id_doctor, created_at, updated_at, active,
                         id_clinic_rol, id_clinic)
                    VALUES
                        (%s, %s, %s,
                         %s,    NOW(),   NULL,   %s,
                         %s, %s)
                    """,
                    (
                        start_date,
                        end_date,
                        notes,
                        id_doctor,
                        active,
                        id_clinic_rol,
                        id_clinic,
                    ),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def update_doctor_clinic(
        self,
        *,
        id_doctor_clinic: int,
        id_doctor: Optional[int] = None,
        id_clinic: Optional[int] = None,
        id_clinic_rol: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: Optional[str] = None,
        active: Optional[str] = None, 
    ) -> None:
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                # 1) Estado actual
                cur.execute(
                    """
                    SELECT id_doctor, id_clinic, id_clinic_rol
                    FROM doctor_clinics
                    WHERE id_doctor_clinic=%s
                    """,
                    (id_doctor_clinic,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("doctor_clinic not found")

                new_id_doctor = id_doctor if id_doctor is not None else row["id_doctor"]
                new_id_clinic = id_clinic if id_clinic is not None else row["id_clinic"]
                new_id_role   = id_clinic_rol if id_clinic_rol is not None else row["id_clinic_rol"]

                # 2) Verificación índice único (ajústalo si tu uk_dc_pair es diferente)
                if (
                    new_id_doctor != row["id_doctor"]
                    or new_id_clinic != row["id_clinic"]
                    or new_id_role   != row["id_clinic_rol"]
                ):
                    cur.execute(
                        """
                        SELECT 1
                        FROM doctor_clinics
                        WHERE id_doctor=%s AND id_clinic=%s AND id_clinic_rol=%s
                          AND id_doctor_clinic <> %s
                        LIMIT 1
                        """,
                        (new_id_doctor, new_id_clinic, new_id_role, id_doctor_clinic),
                    )
                    if cur.fetchone():
                        raise IntegrityError(
                            msg="Duplicate pair for unique constraint uk_dc_pair",
                            errno=1062, sqlstate="23000"
                        )

            # 3) UPDATE dinámico
            sets = []
            params: List[Any] = []
            if start_date is not None:
                sets.append("start_date=%s"); params.append(start_date)
            if end_date is not None:
                sets.append("end_date=%s"); params.append(end_date)
            if notes is not None:
                sets.append("notes=%s"); params.append(notes)
            if id_doctor is not None:
                sets.append("id_doctor=%s"); params.append(id_doctor)
            if id_clinic_rol is not None:
                sets.append("id_clinic_rol=%s"); params.append(id_clinic_rol)
            if id_clinic is not None:
                sets.append("id_clinic=%s"); params.append(id_clinic)
            if active is not None:  # ← columna real
                sets.append("active=%s"); params.append(active)

            sets.append("updated_at=NOW()")

            if len(sets) == 1:
                return  # nada que actualizar

            sql = f"UPDATE doctor_clinics SET {', '.join(sets)} WHERE id_doctor_clinic=%s"
            params.append(id_doctor_clinic)

            with conn.cursor() as cur2:
                cur2.execute(sql, tuple(params))
                conn.commit()
        finally:
            conn.close()
    def delete_doctor_clinic(self, *, id_doctor_clinic: int) -> None:
        """Soft delete: active -> 'inactive' y marca updated_at."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE doctor_clinics
                       SET active='0',
                           updated_at=NOW()
                     WHERE id_doctor_clinic=%s
                    """,
                    (id_doctor_clinic,),
                )
                conn.commit()
        finally:
            conn.close()

    def get_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        """
        Cards básicos. Buscar por notes o filtrar por active.
        """
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_doctor_clinic AS id, id_doctor, id_clinic, id_clinic_rol, "
                    "start_date, end_date, active, notes "
                    "FROM doctor_clinics WHERE active=1"
                )
                params: List[Any] = []
                if search:
                    base += " AND (notes LIKE %s OR active LIKE %s)"
                    like = f"%{search}%"
                    params.extend([like, like])
                base += " ORDER BY id_doctor_clinic DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

doctor_clinics_model = DoctorClinicsModel()

def get_doctor_clinics(id_doctor_clinic: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Si se pasa id -> devuelve uno; si no -> lista de activos primero.
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if id_doctor_clinic:
                cur.execute(
                    """
                    SELECT
                        id_doctor_clinic, start_date, end_date, notes,
                        id_doctor, created_at, updated_at, active,
                        id_clinic_rol, id_clinic
                    FROM doctor_clinics
                    WHERE id_doctor_clinic=%s
                    """,
                    (id_doctor_clinic,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        id_doctor_clinic, start_date, end_date, notes,
                        id_doctor, created_at, updated_at, active,
                        id_clinic_rol, id_clinic
                    FROM doctor_clinics
                    ORDER BY id_doctor_clinic DESC
                    """
                )
            return cur.fetchall()
    finally:
        conn.close()

def get_doctor_clinic_by_id_sql(id_doctor_clinic: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                    id_doctor_clinic, start_date, end_date, notes,
                    id_doctor, created_at, updated_at, active,
                    id_clinic_rol, id_clinic
                FROM doctor_clinics
                WHERE id_doctor_clinic=%s
                LIMIT 1
                """,
                (id_doctor_clinic,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
