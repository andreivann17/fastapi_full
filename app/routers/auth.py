"""
Authentication endpoints.

Defines routes related to logging in. It uses the ``authenticate``
function from ``app.models.auth`` to verify credentials against the
database and issues a JSON Web Token on success. Tokens include the
user's ID and role and have a configurable expiry duration.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..models.auth import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])

# Pydantic models for request/response bodies
class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    """Authenticate a user and return a JWT token."""
    try:
        role, user_id = authenticate(payload.email, payload.password)
    except ValueError as exc:
        # multiple roles case is signalled with a custom string
        if str(exc) == "multiple_roles":
            return {
                "message": "This email exists as both a patient and an administrator. Please select a role to continue.",
                "options": ["admin", "patient"],
            }
        elif str(exc) == "email_not_found":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found")
        elif str(exc) == "invalid_password":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Issue JWT token (MISMA clave que deps.py)
    secret = os.getenv("SECRET_KEY", "secret")
    expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", "2"))
    payload_data = {
        "id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
    }
    token = jwt.encode(payload_data, secret, algorithm="HS256")
    return {"token": token, "role": role}
