# app/models/specialties.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from ..db import get_connection

class SpecialtiesModel:
    def code_exists(self, code: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM specialties WHERE code=%s LIMIT 1", (code,))
                return cur.fetchone() is not None
        finally:
            conn.close()
    def name_exists(self, name: str) -> bool:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM specialties WHERE name=%s LIMIT 1", (name,))
                return cur.fetchone() is not None
        finally:
            conn.close()

    def add_specialty(self, name: str,code:str) -> int:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO specialties (name,code,created_at,active) VALUES (%s,%s,NOW(),1)", (name,code,))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    def update_specialty(self, *, code: str, name: Optional[str]) -> None:
        if name is None:
            return
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE specialties SET name=%s WHERE code=%s",
                    (name, code),
                )
                conn.commit()
        finally:
            conn.close()

    def delete_specialty(self, code: int) -> None:
        """Borrado físico (no hay columna status)."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE specialties set active = 0, updated_at = NOW()  WHERE code=%s", (code,))
                conn.commit()
        finally:
            conn.close()

    def get_cards(self, *, limit: int, search: str = "", offset: int = 0) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                base = "SELECT code AS id, name FROM specialties WHERE active=1"
                params: List[Any] = []
                if search:
                    base += " AND name LIKE %s"
                    params.append(f"%{search}%")
                base += " ORDER BY code DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cur.execute(base, tuple(params))
                return cur.fetchall()
        finally:
            conn.close()

specialties_model = SpecialtiesModel()

def get_specialties(code: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            if code:
                cur.execute(
                    "SELECT code, name FROM specialties WHERE code=%s",
                    (code,),
                )
            else:
                cur.execute("SELECT code, name FROM specialties ORDER BY code DESC")
            return cur.fetchall()
    finally:
        conn.close()

def get_specialty_by_id(code: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT code, name FROM specialties WHERE code=%s",
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()
