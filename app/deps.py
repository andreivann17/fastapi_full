# app/deps.py
"""
Common dependencies.

Provee autenticación JWT para FastAPI mediante HTTP Bearer.
Al usar Security(HTTPBearer), Swagger UI muestra el botón "Authorize".
"""

from __future__ import annotations

import os
from typing import Dict

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# MISMA clave que usa el login (routers/auth.py)
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHMS = ["HS256"]

# Hace que Swagger muestre el botón Authorize
security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict:
    """
    Valida el header Authorization: Bearer <token> y retorna el payload.
    Lanza 401 si no hay header o el token es inválido/expirado.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHMS)
        return payload  # dict con campos como id, role, exp
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
