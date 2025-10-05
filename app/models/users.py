"""
User model functions.

This module contains data access helpers for user‑related operations
such as checking whether an email exists, saving password reset tokens
and updating hashed passwords. It mirrors the original Node.js
implementation but uses the Python ``mysql.connector`` driver.
"""

from __future__ import annotations

import bcrypt
from typing import Optional

from ..db import get_connection


def get_email_exists(email: str) -> bool:
    """Return ``True`` if a user with the given email exists.

    Args:
        email: The email address to look up.

    Returns:
        ``True`` if at least one user exists with the provided email,
        otherwise ``False``.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id_user FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            return row is not None
    finally:
        conn.close()


def validate_code(code: str, email: str) -> bool:
    """Validate a password reset token for the given email.

    Args:
        code: The token string to verify.
        email: The email address associated with the token.

    Returns:
        ``True`` if the token matches an entry in the ``users`` table,
        otherwise ``False``.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id_user FROM users WHERE email = %s AND token = %s",
                (email, code),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def save_token(token: str, email: str) -> None:
    """Persist a password reset token for a user.

    Args:
        token: The token to save.
        email: The email address of the user.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET token = %s WHERE email = %s", (token, email))
            conn.commit()
    finally:
        conn.close()


def update_password(email: str, plaintext_password: str) -> None:
    """Hash a plaintext password and update it for the given user.

    Args:
        email: The email of the user whose password should be updated.
        plaintext_password: The new password in plaintext form.
    """
    # Generate salt and hash the password using bcrypt. We use a cost of
    # 12 rounds which strikes a good balance between security and
    # performance. A higher cost will slow down login attempts slightly.
    salt: bytes = bcrypt.gensalt(rounds=12)
    hashed: bytes = bcrypt.hashpw(plaintext_password.encode("utf-8"), salt)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password = %s WHERE email = %s",
                (hashed.decode("utf-8"), email),
            )
            conn.commit()
    finally:
        conn.close()
