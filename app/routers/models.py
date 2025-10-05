# app/routers/models.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

import logging
from pydantic import BaseModel, ConfigDict

from ..deps import get_current_user
from ..models import models_details as mdl  # mantenemos tu módulo
from fastapi import APIRouter, Depends, File,Query, UploadFile, HTTPException,status
from pathlib import Path
import os, uuid, logging
from ..services.infer_swin_edema_3_clases import predict_image_3  # tu servicio
from ..services.infer_swin_edema_4_clases import predict_image_4  # tu servicio
class ModelBody(BaseModel):
    model_config = ConfigDict(extra="allow")


logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/models", tags=["models"])

# Rutas de trabajo (respetando UPLOADS_DIR montado en main)
BASE_DIR = Path(__file__).resolve().parents[1]                 # .../fastapi_full
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads")))
INBOX_DIR = UPLOADS_DIR / "inbox"
INBOX_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}

def _save_temp(image: UploadFile) -> Path:
    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or 'unknown'}")
    tmp = INBOX_DIR / f"{uuid.uuid4().hex}{suffix}"
    with tmp.open("wb") as f:
        f.write(image.file.read())
    return tmp
@router.get("/", response_model=List[Dict[str, Any]])
def list_models(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, min_length=1),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Lista modelos. Si viene ?search= filtra por description, code, user, task, target_category,
    modality, architecture, framework y region.
    """
    # Normalizar search: si viene vacío o espacios, tratarlo como None.
    if search is not None:
        search = search.strip() or None

    logger.info("GET /models - limit=%s offset=%s search=%r", limit, offset, search)

    # Pasa 'search' por keyword para evitar errores de orden
    res = mdl.getModelsList([limit, offset], search=search)

    # Por si quieres ver cuántos registros regresaste
    try:
        logger.info("GET /models - returned=%d rows", len(res.get("modelDetails", [])))
    except Exception:
        pass

    return res.get("modelDetails", [])

@router.get("/{code}")
def get_by_code(code: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Devuelve exactamente el mismo shape que tu Node:
    { "modelDetails": [...], "dataContent": {...} }
    """
    result = mdl.getModelsDetailsModelInfo(code)
    if not result["modelDetails"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return result


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_one(body: ModelBody, user: Dict[str, Any] = Depends(get_current_user)):
    # Inserta modelo como en addModelModel (requiere name,width,height,task,model_base,code,path, user=id_user)
    required = ("name", "width", "height", "task", "model_base", "code", "path")
    if any(k not in body.model_dump() for k in required):
        raise HTTPException(status_code=400, detail=f"Missing fields: {required}")
    new_id = mdl.addModelModel(
        data=body.model_dump(),
        code=body.model_dump()["code"],
        path=body.model_dump()["path"],
        user=int(user["id"]),
    )
    return {"id": new_id}



@router.post("/edema-tres")
def edema_tres(
    image: UploadFile = File(..., description="Imagen (multipart/form-data, campo 'image')"),
):
    tmp = None
    try:
        tmp = _save_temp(image)
        pred = predict_image_3(str(tmp))  # ← tu Swin
        return {"label": pred["label"], "probs": pred["probs"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("edema_tres failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if tmp and tmp.exists(): tmp.unlink()
        except:  # no rompas la respuesta por limpieza
            pass

@router.post("/edema-cuatro")
def edema_cuatro(
    image: UploadFile = File(..., description="Imagen (multipart/form-data, campo 'image')"),
):
    tmp = None
    try:
        tmp = _save_temp(image)
        # Si después usas otro checkpoint 4 clases, cambia aquí la llamada.
        pred = predict_image_4(str(tmp))
        return {"label": pred["label"], "probs": pred["probs"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("edema_cuatro failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if tmp and tmp.exists(): tmp.unlink()
        except:
            pass

@router.patch("/{code}")
def delete_by_code(code: str, user: Dict[str, Any] = Depends(get_current_user)):
    affected = mdl.deleteModelModel(code, int(user["id"]))
    if not affected:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"ok": True}
