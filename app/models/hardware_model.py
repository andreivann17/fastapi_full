# app/models/hardware_model.py
"""
Migración fiel de hardware_model (Node/Express) a Python/FastAPI.

Incluye:
- getVendorByKey
- getComponentHardwareByKey
- getInfoModel{Diseases|Stages|Biomarkers|Segmentation|FeatureMaps}Server
- checkIfServerExists
- checkIfUuidExists
- addHardwareModel
- addHardwareTypeModel

Mantiene shape y comportamiento. Usa app.db.get_connection() (mysql-connector).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from ..db import get_connection

# -----------------------
# Estado global (como en Node)
# -----------------------
ID_SERVER_ACTIVO: Optional[int] = None
SERVER_TYPES_ACTIVOS: List[Dict[str, Any]] = []


# -----------------------
# Helpers internos
# -----------------------
def _fetch_all(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        cnx.close()


def _fetch_one(sql: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        cnx.close()


def _execute(sql: str, params: Tuple[Any, ...]) -> int:
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            cur.execute(sql, params)
            cnx.commit()
            return cur.lastrowid
    finally:
        cnx.close()


# -----------------------
# Lookups clave → id
# -----------------------
def getVendorByKey(name: str) -> int:
    row = _fetch_one(
        "SELECT id_vendor FROM vendors WHERE name = %s LIMIT 1",
        (name,),
    )
    if not row:
        raise ValueError("Vendor not found")
    return int(row["id_vendor"])


def getComponentHardwareByKey(name: str) -> int:
    row = _fetch_one(
        "SELECT id_component_hardware FROM components_hardware WHERE name = %s LIMIT 1",
        (name,),
    )
    if not row:
        raise ValueError("Component Hardware not found")
    return int(row["id_component_hardware"])


# -----------------------
# Info de servidores por tipo de tarea
# -----------------------
def getInfoModelDiseasesServer(idModel: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT 
        s.id_server,
        MAX(s.name)       AS server_name,
        MAX(s.datetime)   AS datetime,
        MAX(st.ram)       AS ram,
        MAX(st.name)      AS model_name,
        MAX(v.name)       AS vendor_name,
        MAX(ch.name)      AS component_name,
        AVG(dm.time_inference) AS avg_inference_time,
        MIN(dm.time_inference) AS min_inference_time,
        MAX(dm.time_inference) AS max_inference_time
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    LEFT JOIN vendors             v ON v.id_vendor = st.id_vendor
    LEFT JOIN detection_models   dm ON dm.id_server_type = st.id_server_type
    JOIN detection_diseases      dd ON dd.id_detection_model = dm.id_detection_model
    JOIN model_diseases          md ON md.id_model_disease = dd.id_model_disease
    JOIN model                    m ON m.id_model = md.id_model
    WHERE m.id_model = %s
      AND dm.time_inference IS NOT NULL
    GROUP BY s.id_server
    """
    return _fetch_all(sql, (idModel,))


def getInfoModelStagesServer(idModel: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT 
        s.id_server,
        MAX(s.name)       AS server_name,
        MAX(s.datetime)   AS datetime,
        MAX(st.ram)       AS ram,
        MAX(st.name)      AS model_name,
        MAX(v.name)       AS vendor_name,
        MAX(ch.name)      AS component_name,
        AVG(dm.time_inference) AS avg_inference_time,
        MIN(dm.time_inference) AS min_inference_time,
        MAX(dm.time_inference) AS max_inference_time
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    LEFT JOIN vendors             v ON v.id_vendor = st.id_vendor
    LEFT JOIN detection_models   dm ON dm.id_server_type = st.id_server_type
    JOIN detection_stages        ds ON ds.id_detection_model = dm.id_detection_model
    JOIN model_stages            ms ON ms.id_model_stage = ds.id_model_stage
    JOIN model                    m ON m.id_model = ms.id_model
    WHERE m.id_model = %s
      AND dm.time_inference IS NOT NULL
    GROUP BY s.id_server
    """
    return _fetch_all(sql, (idModel,))


def getInfoModelBiomarkersServer(idModel: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT 
        s.id_server,
        MAX(s.name)       AS server_name,
        MAX(s.datetime)   AS datetime,
        MAX(st.ram)       AS ram,
        MAX(st.name)      AS model_name,
        MAX(v.name)       AS vendor_name,
        MAX(ch.name)      AS component_name,
        AVG(dm.time_inference) AS avg_inference_time,
        MIN(dm.time_inference) AS min_inference_time,
        MAX(dm.time_inference) AS max_inference_time
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    LEFT JOIN vendors             v ON v.id_vendor = st.id_vendor
    LEFT JOIN detection_models   dm ON dm.id_server_type = st.id_server_type
    JOIN detection_biomarkers    db ON db.id_detection_model = dm.id_detection_model
    JOIN model_biomarkers        mb ON mb.id_model_biomarker = db.id_model_biomarker
    JOIN model                    m ON m.id_model = mb.id_model
    WHERE m.id_model = %s
      AND dm.time_inference IS NOT NULL
    GROUP BY s.id_server
    """
    return _fetch_all(sql, (idModel,))


def getInfoModelSegmentationServer(idModel: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT 
        s.id_server,
        MAX(s.name)       AS server_name,
        MAX(s.datetime)   AS datetime,
        MAX(st.ram)       AS ram,
        MAX(st.name)      AS model_name,
        MAX(v.name)       AS vendor_name,
        MAX(ch.name)      AS component_name,
        AVG(dm.time_inference) AS avg_inference_time,
        MIN(dm.time_inference) AS min_inference_time,
        MAX(dm.time_inference) AS max_inference_time
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    LEFT JOIN vendors             v ON v.id_vendor = st.id_vendor
    LEFT JOIN detection_models   dm ON dm.id_server_type = st.id_server_type
    JOIN detection_segmentations ds ON ds.id_detection_model = dm.id_detection_model
    JOIN model                    m ON m.id_model = ds.id_model
    WHERE m.id_model = %s
      AND dm.time_inference IS NOT NULL
    GROUP BY s.id_server
    """
    return _fetch_all(sql, (idModel,))


def getInfoModelFeatureMapsServer(idModel: int) -> List[Dict[str, Any]]:
    sql = """
    SELECT 
        s.id_server,
        MAX(s.name)       AS server_name,
        MAX(s.datetime)   AS datetime,
        MAX(st.ram)       AS ram,
        MAX(st.name)      AS model_name,
        MAX(v.name)       AS vendor_name,
        MAX(ch.name)      AS component_name,
        AVG(dm.time_inference) AS avg_inference_time,
        MIN(dm.time_inference) AS min_inference_time,
        MAX(dm.time_inference) AS max_inference_time
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    LEFT JOIN vendors             v ON v.id_vendor = st.id_vendor
    LEFT JOIN detection_models   dm ON dm.id_server_type = st.id_server_type
    JOIN detection_features_maps dfp ON dfp.id_detection_model = dm.id_detection_model
    JOIN model                    m ON m.id_model = dfp.id_model
    WHERE m.id_model = %s
      AND dm.time_inference IS NOT NULL
    GROUP BY s.id_server
    """
    return _fetch_all(sql, (idModel,))


# -----------------------
# Existencia de server / uuid
# -----------------------
def checkIfServerExists() -> List[Dict[str, Any]]:
    # Igual que en Node: solo verifica que haya registros de server
    return _fetch_all("SELECT id_server FROM server")


def checkIfUuidExists(uuid: str) -> List[Dict[str, Any]]:
    sql = """
    SELECT
        st.id_server_type,
        ch.name,
        s.id_server
    FROM server s
    LEFT JOIN server_type        st ON st.id_server = s.id_server
    LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
    WHERE s.uuid = %s
    LIMIT 1
    """
    # Nota: el Node hace LIMIT 1 pero luego usa el arreglo completo; aquí devolvemos
    # lo que haya (puede venir 1 fila por el LIMIT). Si necesitas todas las filas,
    # quita el LIMIT 1.
    rows = _fetch_all(sql, (uuid,))
    return rows


# -----------------------
# Altas (server + tipos)
# -----------------------
def addHardwareTypeModel(idServer: int, hwData: Dict[str, Any]) -> Dict[str, Any]:
    """
    hwData: { type, vendor, name, ram }
    """
    idComponentHardware = getComponentHardwareByKey(str(hwData["type"]))
    idVendor = getVendorByKey(str(hwData["vendor"]))
    insert_id = _execute(
        """
        INSERT INTO server_type (id_server, id_component_hardware, name, id_vendor, ram)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (idServer, idComponentHardware, hwData.get("name"), idVendor, hwData.get("ram")),
    )
    # Para compatibilidad con Node (usa result.insertId):
    return {"insertId": insert_id}


def addHardwareModel(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    data esperado:
    {
      "server_name": str,
      "uuid": str,
      "content": [
        { "type": "GPU", "vendor": "NVIDIA", "name": "A100", "ram": "40GB" },
        ...
      ]
    }
    """
    global ID_SERVER_ACTIVO, SERVER_TYPES_ACTIVOS

    exists = checkIfUuidExists(str(data["uuid"]))
    exists_server = checkIfServerExists()

    # Caso: ya existe
    if len(exists) > 0 and len(exists_server) > 0:
        id_existente = int(exists[0]["id_server"])
        ID_SERVER_ACTIVO = id_existente

        # reconstruir SERVER_TYPES_ACTIVOS a partir de la consulta (como Node)
        SERVER_TYPES_ACTIVOS = [
            {"id_server_type": row["id_server_type"], "type": row["name"]} for row in exists
        ]

        return {
            "message": "UUID ya existe. No se insertó nada.",
            "id_server": id_existente,
            "types": SERVER_TYPES_ACTIVOS,
        }

    # Caso: no existe -> insertar server
    server_id = _execute(
        "INSERT INTO server (name, uuid, datetime) VALUES (%s, %s, NOW())",
        (data.get("server_name"), str(data["uuid"])),
    )
    ID_SERVER_ACTIVO = server_id
    SERVER_TYPES_ACTIVOS = []

    # Insertar tipos de hardware y armar respuesta
    tipos: List[Dict[str, Any]] = []
    for hw in data.get("content", []):
        res = addHardwareTypeModel(server_id, hw)  # {"insertId": ...}
        tipos.append({"id_server_type": res["insertId"], "type": hw.get("type")})

    SERVER_TYPES_ACTIVOS = tipos

    return {"serverId": server_id, "types": tipos}