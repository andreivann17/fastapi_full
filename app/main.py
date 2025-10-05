# app/main.py
"""
Entry point for the unified FastAPI application.

- Configura CORS y healthcheck
- Inicializa el pool de MySQL
- Limpia directorio de tempmodels al arrancar
- Registra routers
- Inyecta SecurityScheme HTTP Bearer en OpenAPI para mostrar "Authorize" en Swagger
"""

from __future__ import annotations
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from .db import init_pool
from .utils.clean_temp_models import clean_temp_models

# Routers
from .routers import (
    auth, doctor_clinics, users, patients, records, 
    detections, diagnostic, doctors,specialties, clinics,clinics_roles,arquitectures,biomarkers,
    patients_visits,doctor_specialties)
from .routers import models as models_router


# ----- App -----
app = FastAPI(title="Unified API", version="1.0.0", openapi_url="/openapi.json")
BASE_DIR = Path(__file__).resolve().parent.parent      # -> .../fastapi_full
# Permite override por variable de entorno UPLOADS_DIR si quieres cambiar ubicación
DEFAULT_UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(DEFAULT_UPLOADS_DIR)))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)  # asegura que exista, sino StaticFiles truena

# ----- CORS -----


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://192.168.1.10:3000"],   # no uses "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Authorization"],          # opcional
)

# Healthcheck
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Startup: pool + limpieza tempmodels
@app.on_event("startup")
def on_startup():
    init_pool()
    try:
        clean_temp_models()
    except Exception:
        # No romper arranque por problemas de FS
        pass

# ----- Swagger: SecurityScheme global para que aparezca "Authorize" -----
BEARER_SCHEME_NAME = "HTTPBearer"

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Unified API",
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    if BEARER_SCHEME_NAME not in security_schemes:
        security_schemes[BEARER_SCHEME_NAME] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# ----- Include Routers -----
# auth y users quedan públicos (login/reset)
app.include_router(auth.router)
app.include_router(users.router)

# Para que Swagger marque con candado y, al autorizar, envíe Authorization automáticamente.
secured_dependency = Security(HTTPBearer())
app.include_router(models_router.router)
app.include_router(patients.router, dependencies=[secured_dependency])
app.include_router(records.router, dependencies=[secured_dependency])
app.include_router(clinics.router, dependencies=[secured_dependency])
app.include_router(doctor_specialties.router, dependencies=[secured_dependency])
app.include_router(clinics_roles.router, dependencies=[secured_dependency])
app.include_router(doctor_clinics.router, dependencies=[secured_dependency])
app.include_router(patients_visits.router, dependencies=[secured_dependency])
app.include_router(specialties.router, dependencies=[secured_dependency])
app.include_router(doctors.router, dependencies=[secured_dependency])
app.include_router(detections.router, dependencies=[secured_dependency])
app.include_router(diagnostic.router, dependencies=[secured_dependency])
