# app/models/auth.py
"""
Auth utils.

- Autentica en `users` y, si existe columna `password`, también en `patients`.
- Soporta hashes bcrypt guardados como VARCHAR/VARBINARY/BLOB/CHAR(60)
  (hace strip de espacios y convierte a bytes).
- Evita error si `patients.password` no existe.
- Fallback opcional a texto plano (solo migración) con ALLOW_PLAINTEXT_PASSWORDS=1.
- Lanza ValueError: "multiple_roles" | "email_not_found" | "invalid_password".
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

import bcrypt

from ..db import get_connection


def _to_bytes(x) -> bytes:
    """
    Convierte str/bytes/bytearray/memoryview/None a bytes para bcrypt.checkpw,
    aplicando strip() para eliminar relleno (p.ej., CHAR(60) con espacios).
    """
    if x is None:
        return b""
    if isinstance(x, bytes):
        return x.strip()
    if isinstance(x, bytearray):
        return bytes(x).strip()
    if isinstance(x, memoryview):
        return x.tobytes().strip()
    # str
    return str(x).strip().encode("utf-8")


def _is_bcrypt_hash(b: bytes) -> bool:
    """
    Heurística mínima: bcrypt suele empezar con $2a$/$2b$/$2y$ y ~60 chars.
    Se hace strip antes de checar.
    """
    b = (b or b"").strip()
    try:
        s = b.decode("utf-8", errors="ignore")
    except Exception:
        return False
    s = s.strip()
    return (s.startswith("$2a$") or s.startswith("$2b$") or s.startswith("$2y$")) and (55 <= len(s) <= 100)


def _allow_plaintext() -> bool:
    """Permite comparar en texto plano (solo migración)."""
    val = os.getenv("ALLOW_PLAINTEXT_PASSWORDS", "0").strip().lower()
    return val in ("1", "true", "yes", "y")


def _table_has_column(table: str, column: str) -> bool:
    """
    True si la columna existe en la tabla (usa DB activa de la conexión;
    si no, cae a MYSQL_DATABASE).
    """
    cnx = get_connection()
    try:
        db_name = getattr(cnx, "database", None) or os.getenv("MYSQL_DATABASE", "")
        with cnx.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
                """,
                (db_name, table, column),
            )
            (count,) = cur.fetchone()
            return count > 0
    finally:
        cnx.close()


def _fetch_credentials(table: str, email: str) -> Optional[Tuple[int, bytes]]:
    """
    Retorna (id, hashed_password) de la tabla indicada.
    Para 'patients', solo consulta si existe la columna 'password'.
    """
    if table == "patients" and not _table_has_column("patients", "password"):
        return None  # no hay columna password en patients; omitir

    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            if table == "users":
                cur.execute("SELECT id_user, password FROM users WHERE email = %s", (email,))
            elif table == "patients":
                cur.execute("SELECT id_patient, password FROM patients WHERE email = %s", (email,))
            else:
                raise ValueError("invalid table: expected 'users' or 'patients'")

            row = cur.fetchone()
            if not row:
                return None

            user_id = row[0]
            stored = _to_bytes(row[1])  # hace strip + bytes
            return (user_id, stored)
    finally:
        cnx.close()


def _verify_password(plain: str, stored: bytes) -> bool:
    """
    Verifica contraseña:
      - Si stored parece bcrypt -> bcrypt.checkpw
      - Si NO parece bcrypt -> (opcional) compara texto plano si ALLOW_PLAINTEXT_PASSWORDS=1
    """
    stored = (stored or b"").strip()
    if _is_bcrypt_hash(stored):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored)
        except Exception:
            return False
    if _allow_plaintext():
        try:
            return plain == stored.decode("utf-8", errors="ignore")
        except Exception:
            return False
    return False


def authenticate(email: str, password: str) -> Tuple[str, int]:
    """
    Autentica contra 'users' y (si existe columna password) contra 'patients'.
    Retorna ('admin'|'patient', id). Lanza ValueError:
      - "multiple_roles" | "email_not_found" | "invalid_password"
    """
    user_row = _fetch_credentials("users", email)
    patient_row = _fetch_credentials("patients", email)

    # existe en ambas tablas
    if user_row and patient_row:
        raise ValueError("multiple_roles")

    # solo paciente
    if patient_row and not user_row:
        pid, stored = patient_row
        if not stored or not _verify_password(password, stored):
            raise ValueError("invalid_password")
        return ("patient", pid)

    # solo usuario (admin)
    if user_row and not patient_row:
        uid, stored = user_row
        if not stored or not _verify_password(password, stored):
            raise ValueError("invalid_password")
        return ("admin", uid)

    raise ValueError("email_not_found")
