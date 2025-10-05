"""
Funciones para la tabla `model` y detalles por `code`.

Replica el comportamiento de:
getModelsDetailsModelInfo(code):
- SELECT con LEFT JOINs (task, model_base, users, arquitectures, frameworks,
  model_modalities, modalities, regions, model_yolo_preprocessor, model_filter_image)
- Devuelve {"modelDetails": [...], "dataContent": {...}}
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..db import get_connection

TABLE = "model"


def _columns() -> List[str]:
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(f"SHOW COLUMNS FROM {TABLE}")
            return [r["Field"] for r in cur.fetchall()]
    finally:
        cnx.close()


def list_models(limit: int = 50, offset: int = 0, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Listado simple con paginación (usa columna 'name' si existe para search)."""
    cols = _columns()
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            sql = f"SELECT * FROM {TABLE}"
            params: List[Any] = []
            if search and "name" in cols:
                sql += " WHERE name LIKE %s"
                params.append(f"%{search}%")
            sql += " ORDER BY 1 DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    finally:
        cnx.close()


def get_model(model_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un registro por su PK (por si lo necesitas en otros flujos)."""
    # Detecta PK
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(f"SHOW KEYS FROM {TABLE} WHERE Key_name='PRIMARY'")
            pk_row = cur.fetchone()
            if not pk_row:
                raise RuntimeError(f"No PRIMARY KEY en tabla {TABLE}")
            pk = pk_row["Column_name"]
            cur.execute(f"SELECT * FROM {TABLE} WHERE {pk}=%s", (model_id,))
            return cur.fetchone()
    finally:
        cnx.close()


def _get_yolo_preprocessor(id_model: int) -> List[Dict[str, Any]]:
    """Contenido auxiliar: filas de model_yolo_preprocessor (si existen)."""
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT *
                FROM model_yolo_preprocessor
                WHERE id_model = %s
                """,
                (id_model,),
            )
            return cur.fetchall()
    finally:
        cnx.close()


def _get_filters(id_model: int) -> List[Dict[str, Any]]:
    """Contenido auxiliar: filas de model_filter_image (si existen)."""
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT *
                FROM model_filter_image
                WHERE id_model = %s
                """,
                (id_model,),
            )
            return cur.fetchall()
    finally:
        cnx.close()


def _get_modalities(id_model: int) -> List[Dict[str, Any]]:
    """Contenido auxiliar: modalidades/regiones asociadas al modelo."""
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT
                    mm.id_modality,
                    moda.name   AS modality_name,
                    r.name      AS region_name,
                    moda.id_region,
                    moda.description AS modality_description
                FROM model_modalities mm
                LEFT JOIN modalities moda ON moda.id_modality = mm.id_modality
                LEFT JOIN regions    r    ON r.id_region     = moda.id_region
                WHERE mm.id_model = %s
                """,
                (id_model,),
            )
            return cur.fetchall()
    finally:
        cnx.close()


def get_info_model_content(id_model: int, task_key: Optional[str]) -> Dict[str, Any]:
    """
    Equivalente a getInfoModelContent(id_model, task_key) de tu Node.
    - Agrega yolo_preprocessor, filters y modalities si existen.
    - task_key se conserva por compatibilidad (si después quieres lógica por tarea).
    """
    content: Dict[str, Any] = {}
    try:
        yp = _get_yolo_preprocessor(id_model)
        if yp:
            content["yolo_preprocessor"] = yp
    except Exception:
        content.setdefault("yolo_preprocessor", [])

    try:
        flt = _get_filters(id_model)
        if flt:
            content["filters"] = flt
    except Exception:
        content.setdefault("filters", [])

    try:
        mods = _get_modalities(id_model)
        if mods:
            content["modalities"] = mods
    except Exception:
        content.setdefault("modalities", [])

    return content


def get_model_details_by_code(code: Optional[str]) -> Dict[str, Any]:
    """
    Réplica fiel del SELECT con LEFT JOINs que pasaste en Node,
    usando `code` como filtro (si lo provees). Devuelve:
    { "modelDetails": [...], "dataContent": {...} }
    """
    params: List[Any] = []
    where = ""
    if code:
        where = " WHERE m.code = %s"
        params.append(code)

    sql = f"""
        SELECT 
            m.id_model, 
            m.description     AS name, 
            m.input_size,
            m.path_weights    AS path, 
            m.id_task, 
            m.id_target_category,
            tc.name           AS target_category_name,
            m.active, 
            m.id_model_base, 
            mb.name           AS model_base_name, 
            m.datetime, 
            m.id_user, 
            u.name            AS user_name,
            mb.id_arquitecture,
            mb.id_framework, 
            a.name            AS arquitecture_name, 
            f.name            AS framework_name,
            mm.id_modality,
            moda.name         AS modality_name,
            m.code,
            t.task_key,
            t.name            AS task_name,
            r.name            AS region_name,

            /* flags de existencia */
            CASE WHEN myp.id_model IS NOT NULL THEN 1 ELSE 0 END AS has_yolo_preprocessor,
            CASE WHEN mf.id_model  IS NOT NULL THEN 1 ELSE 0 END AS has_filter

        FROM model m 
        LEFT JOIN task             t   ON m.id_task       = t.id_task 
        LEFT JOIN target_category             tc   ON m.id_target_category       = tc.id_target_category
        LEFT JOIN model_base       mb  ON mb.id_model_base= m.id_model_base 
        LEFT JOIN users            u   ON u.id_user       = m.id_user 
        LEFT JOIN arquitectures    a   ON a.id_arquitecture = mb.id_arquitecture 
        LEFT JOIN frameworks       f   ON f.id_framework    = mb.id_framework 
        LEFT JOIN model_modalities mm  ON mm.id_model     = m.id_model 
        LEFT JOIN model_yolo_preprocessor myp ON myp.id_model = m.id_model 
        LEFT JOIN model_filter_image mf       ON mf.id_model  = m.id_model
        LEFT JOIN modalities       moda ON moda.id_modality = mm.id_modality 
        LEFT JOIN regions          r    ON r.id_region     = moda.id_region 
        {where}
        ORDER BY m.id_model DESC
    """

    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(sql, tuple(params))
            model_details = cur.fetchall()

        if not model_details:
            return {"modelDetails": [], "dataContent": {}}

        first = model_details[0]
        data_content = get_info_model_content(first["id_model"], first.get("task_key"))

        return {"modelDetails": model_details, "dataContent": data_content}

    finally:
        cnx.close()
