"""
User related endpoints.

This router exposes endpoints for password reset flow: requesting a
reset token, validating the token and setting a new password. It
makes use of helper functions in ``app.models.users`` and sends
emails via ``smtplib``.
"""

from __future__ import annotations

import os
import secrets
import smtplib
from email.message import EmailMessage
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from ..models.users import get_email_exists, save_token, validate_code, update_password

router = APIRouter(prefix="/users", tags=["users"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetValidate(BaseModel):
    email: EmailStr
    code: str


class PasswordResetUpdate(BaseModel):
    email: EmailStr
    password: str


def _send_reset_email(to_email: str, token: str) -> None:
    """Send a password reset email containing the token.

    Args:
        to_email: Recipient's email address.
        token: The reset token to include in the message body.
    """
    # Compose the email message
    message = f"""
Greetings from the OpenMind team,

We have received a request to reset the password for the account associated with this email address. Please copy the code below and use it in the application:

{token}

If you did not request a password reset, you can safely ignore this email.

Rest assured that your OpenMind account is secure.

OpenMind will never email you to request your password, credit card details, or bank account information.

If you receive a suspicious email containing a link to update your account information, do not click on it. However, please report such emails to OpenMind so we can investigate.

For help and support, visit our Support Center at https://openmind.com/support

Thank you for using OpenMind HR.

Sincerely,
The Innovation & Development Department
OpenMind
"""
    email_message = EmailMessage()
    email_message["Subject"] = "Restablecimiento de contraseña - OpenMind"
    email_message["From"] = os.getenv("RESET_EMAIL_FROM", "Openmind RRHH <noreply@example.com>")
    email_message["To"] = to_email
    email_message.set_content(message)

    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(email_message)
    except Exception as exc:
        raise RuntimeError(f"Error sending email: {exc}")


@router.post("/password/reset")
def request_password_reset(payload: PasswordResetRequest) -> Dict[str, Any]:
    """Generate and send a password reset token to the user via email."""
    email = payload.email
    if not get_email_exists(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not registered")
    # Generate a random token (10 hex characters)
    token = secrets.token_hex(5)
    # Save token in DB
    save_token(token, email)
    # Send email
    try:
        _send_reset_email(email, token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return {"status": True}


@router.post("/password/validate")
def validate_reset_code(payload: PasswordResetValidate) -> Dict[str, Any]:
    """Validate a password reset code."""
    if validate_code(payload.code, payload.email):
        return {"status": True}
    return {"status": False}


@router.post("/password/update")
def update_password_handler(payload: PasswordResetUpdate) -> Dict[str, Any]:
    """Update a user's password after validating the reset token."""
    # Ensure the email exists
    if not get_email_exists(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not registered")
    update_password(payload.email, payload.password)
    return {"status": True}
