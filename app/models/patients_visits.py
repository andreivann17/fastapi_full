# app/models/patient_visits.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection

class PatientVisitsModel:
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM patient_visits WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def add_visit(
        self,
        *,
        code: str,
        id_patient: int,
        dt: str,              # 'YYYY-MM-DD HH:MM:SS'
        id_doctor: int,
        id_clinic: int,
        active: int = 1,
    ) -> int:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO patient_visits
                        (id_patient, datetime, id_doctor, id_clinic, active, code)
                    VALUES
                        (%s,         %s,       %s,        %s,        %s,     %s)
                    """,
                    (id_patient, dt, id_doctor, id_clinic, active, code),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def edit_visit_by_code(self, data: Dict[str, Any]) -> None:
        """
        Actualiza por 'code'. Acepta: id_patient, datetime, id_doctor, id_clinic, active, code
        """
        conn = get_connection()
        try:
            sets = []
            params: List[Any] = []
            if "id_patient" in data:
                sets.append("id_patient=%s"); params.append(data["id_patient"])
            if "datetime" in data:
                sets.append("datetime=%s"); params.append(data["datetime"])
            if "id_doctor" in data:
                sets.append("id_doctor=%s"); params.append(data["id_doctor"])
            if "id_clinic" in data:
                sets.append("id_clinic=%s"); params.append(data["id_clinic"])
            if "active" in data:
                sets.append("active=%s"); params.append(data["active"])

            if not sets:
                return  # nada que actualizar

            sql = f"UPDATE patient_visits SET {', '.join(sets)} WHERE code=%s"
            params.append(data["code"])

            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                conn.commit()
        finally:
            conn.close()

    def delete_visit(self, code: str) -> None:
        """Soft delete -> active = 0."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE patient_visits SET active=0 WHERE code=%s",
                    (code,),
                )
                conn.commit()
        finally:
            conn.close()

    def get_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        """
        Cards básicos: id, code, datetime, id_patient, id_doctor, id_clinic. Solo activos.
        """
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = (
                    "SELECT id_patient_visit AS id, code, datetime, id_patient, id_doctor, id_clinic "
                    "FROM patient_visits WHERE active=1"
                )
                params: List[Any] = []
                if search:
                    base += " AND (code LIKE %s)"
                    params.append(f"%{search}%")
                base += " ORDER BY id_patient_visit DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

patient_visits_model = PatientVisitsModel()

def get_patient_visits(id_patient_visit: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if id_patient_visit:
                cur.execute(
                    """
                    SELECT id_patient_visit, id_patient, datetime, id_doctor, id_clinic, active, code
                    FROM patient_visits
                    WHERE id_patient_visit=%s
                    """,
                    (id_patient_visit,),
                )
            else:
                cur.execute(
                    """
                    SELECT id_patient_visit, id_patient, datetime, id_doctor, id_clinic, active, code
                    FROM patient_visits
                    WHERE active=1
                    ORDER BY id_patient_visit DESC
                    """
                )
            return cur.fetchall()
    finally:
        conn.close()

def get_visit_by_code_sql(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT id_patient_visit, id_patient, datetime, id_doctor, id_clinic, active, code
                FROM patient_visits
                WHERE code=%s
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
