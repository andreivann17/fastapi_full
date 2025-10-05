"""
Diagnostic endpoints.

Expose endpoints for running the combined diagnostic workflow defined
in ``tasks.diagnostic``. These endpoints mirror the original
FastAPI implementation in the provided ``sin_env/main.py`` and
support both a basic diagnostic and a follow‑up chat based on a
selected disease.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import JSONResponse

try:
    from ..tasks import diagnostic as diagnostic_task
except ImportError:
    diagnostic_task = None


router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.post("/")
def run_diagnostic(
    image_path: str = Body(...),
    image_id: str = Body(...),
) -> JSONResponse:
    """Run the end‑to‑end diagnostic pipeline on an image."""
    if diagnostic_task is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Diagnostic task not available")
    try:
        results = diagnostic_task.predict_image(image_path)
        return JSONResponse(content=json.loads(json.dumps({"results": results}, default=str)))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/chat")
def run_chat_diagnostic(
    image_path: str = Body(...),
    image_id: str = Body(...),
    id_disease: str = Body(...),
) -> JSONResponse:
    """Run a chat follow‑up diagnostic.

    The underlying ``diagnostic.predict_image`` function currently
    accepts only a single argument (the image path) and will ignore
    additional parameters. The ``id_disease`` argument is therefore
    accepted for API parity but is not used in the call.
    """
    if diagnostic_task is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Diagnostic task not available")
    try:
        # In the original code a different image root was joined; here we assume
        # ``image_path`` is absolute or relative to the working directory.
        results = diagnostic_task.predict_image(image_path)
        return JSONResponse(content=json.loads(json.dumps({"results": results}, default=str)))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
