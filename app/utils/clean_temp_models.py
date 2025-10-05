# app/utils/clean_temp_models.py
"""
Limpieza de carpetas/archivos temporales de modelos.

Elimina subdirectorios y archivos con antigüedad > max_age_hours dentro de
`uploads/tempmodels` (por defecto), o el path definido por la variable
de entorno `TEMP_MODELS_DIR`.

Uso:
    from app.utils.clean_temp_models import clean_temp_models
    removed = clean_temp_models()  # retorna cuántos items borró
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional


def _default_tempmodels_dir() -> Path:
    # Este archivo vive en fastapi_full/app/utils/clean_temp_models.py
    # Raíz del proyecto = parents[2]
    root = Path(__file__).resolve().parents[2]
    return root / "uploads" / "tempmodels"


def clean_temp_models(max_age_hours: int = 24, base_dir: Optional[str | Path] = None) -> int:
    """
    Elimina directorios/archivos viejos dentro del directorio de tempmodels.

    Args:
        max_age_hours: antigüedad máxima en horas antes de eliminar.
        base_dir: ruta base a usar; si None, usa TEMP_MODELS_DIR o la ruta por defecto.

    Returns:
        Número de entradas eliminadas.
    """
    env_dir = os.getenv("TEMP_MODELS_DIR")
    base = Path(base_dir) if base_dir else (Path(env_dir) if env_dir else _default_tempmodels_dir())

    if not base.exists():
        return 0

    now = time.time()
    removed = 0

    for entry in list(base.iterdir()):
        try:
            mtime = entry.stat().st_mtime
            age_hours = (now - mtime) / 3600.0
            if age_hours <= max_age_hours:
                continue

            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
            else:
                entry.unlink(missing_ok=True)
                removed += 1
        except Exception:
            # No interrumpir por errores de IO puntuales
            continue

    return removed
