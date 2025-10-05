# app/models/clinics_roles.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection

class ClinicsRolesModel:
    def name_exists(self, name: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM clinics_roles WHERE name=%s LIMIT 1", (name,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def add_role(self, *, name: str) -> int:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO clinics_roles (name) VALUES (%s)",
                    (name,),
                )
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def update_role(self, *, id_clinic_rol: int, name: str) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE clinics_roles SET name=%s WHERE id_clinic_rol=%s",
                    (name, id_clinic_rol),
                )
                conn.commit()
        finally:
            conn.close()

    def delete_role(self, *, id_clinic_rol: int) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM clinics_roles WHERE id_clinic_rol=%s", (id_clinic_rol,))
                conn.commit()
        finally:
            conn.close()

    def get_roles_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = "SELECT id_clinic_rol AS id, name FROM clinics_roles WHERE active=1"
                params: List[Any] = []
                if search:
                    base += " AND name LIKE %s"
                    params.append(f"%{search}%")
                base += " ORDER BY id_clinic_rol DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

clinics_roles_model = ClinicsRolesModel()

def get_clinics_roles(id_clinic_rol: Optional[int] = None) -> List[Dict[str, Any]]:
    """Devuelve todos o uno por id."""
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if id_clinic_rol:
                cur.execute(
                    "SELECT id_clinic_rol, name FROM clinics_roles WHERE id_clinic_rol=%s",
                    (id_clinic_rol,),
                )
            else:
                cur.execute(
                    "SELECT id_clinic_rol, name FROM clinics_roles ORDER BY id_clinic_rol DESC"
                )
            return cur.fetchall()
    finally:
        conn.close()

def get_role_by_id(id_clinic_rol: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id_clinic_rol, name FROM clinics_roles WHERE id_clinic_rol=%s",
                (id_clinic_rol,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
