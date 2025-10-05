# app/models/models_details.py
"""
Migración fiel de modelsDetails de Node a Python/FastAPI.

Incluye:
- getTaskIdByKey
- addModel* (todas las variantes)
- Combos (tasks, modalities, base, diseases, stages, biomarkers, filters, object detection base)
- Info por tipo (features_maps, diseases, stages, object_detection, segmentation, biomarkers)
- Estadísticas y agrupaciones de imágenes
- getInfoModelContent (switch por task_key)
- getModelsDetailsModelInfo (SELECT con JOINs + dataContent)
- getModelsModelCards
- deleteModelModel (soft delete por code)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from ..db import get_connection
from .hardware_model import (
    getInfoModelBiomarkersServer,
    getInfoModelDiseasesServer,
    getInfoModelSegmentationServer,
    getInfoModelStagesServer,
    getInfoModelFeatureMapsServer,
)

# ---------------------------
# Utilidades base / helpers
# ---------------------------

def _fetch_one(sql: str, params: tuple) -> Optional[Dict[str, Any]]:
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row
    finally:
        cnx.close()


def _fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cnx = get_connection()
    try:
        with cnx.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        cnx.close()


def _execute(sql: str, params: tuple) -> int:
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            cur.execute(sql, params)
            cnx.commit()
            return cur.lastrowid
    finally:
        cnx.close()


# ---------------------------
# Core: tasks / inserts
# ---------------------------

def getTaskIdByKey(task_key: str) -> int:
    row = _fetch_one("SELECT id_task FROM task WHERE task_key=%s LIMIT 1", (task_key,))
    if not row:
        raise ValueError("Task key not found")
    return int(row["id_task"])


def addModelModalityModel(id_model: int, id_modality: int) -> int:
    return _execute(
        """
        INSERT INTO model_modalities (id_model, id_modality)
        VALUES (%s, %s)
        """,
        (id_model, id_modality),
    )


def addModelFilterModel(id_model: int, id_filter: int) -> int:
    return _execute(
        """
        INSERT INTO model_filter_image (id_model, id_filter_image)
        VALUES (%s, %s)
        """,
        (id_model, id_filter),
    )


def addModelYOLOPreprocessingModel(id_model: int, id_model_required: int, class_detection: str) -> int:
    return _execute(
        """
        INSERT INTO model_yolo_preprocessor (id_model, id_model_required, class_detection)
        VALUES (%s, %s, %s)
        """,
        (id_model, id_model_required, class_detection),
    )


def addModelObjectDetectionModel(id_model: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sql = """
        INSERT INTO model_object_detection (id_model, id_biomarker, index_class)
        VALUES (%s, %s, %s)
    """
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            counter = 0
            for item in classes:
                cur.execute(sql, (id_model, item["id"], counter))
                counter += 1
            cnx.commit()
        return {"message": "All biomarkers inserted successfully"}
    finally:
        cnx.close()


def addModelBiomarkersModel(id_model: int, id_disease: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sql = """
        INSERT INTO model_biomarkers (id_model, id_biomarker, id_disease, index_class)
        VALUES (%s, %s, %s, %s)
    """
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            counter = 0
            for item in classes:
                cur.execute(sql, (id_model, item["id"], id_disease, counter))
                counter += 1
            cnx.commit()
        return {"message": "All biomarkers inserted successfully"}
    finally:
        cnx.close()


def addModelStagesModel(id_model: int, id_disease: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sql = """
        INSERT INTO model_stages (id_model, id_stage, id_disease, index_class)
        VALUES (%s, %s, %s, %s)
    """
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            counter = 0
            for item in classes:
                cur.execute(sql, (id_model, item["id"], id_disease, counter))
                counter += 1
            cnx.commit()
        return {"message": "All stages inserted successfully"}
    finally:
        cnx.close()


def addModelDiseasesModel(id_model: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sql = """
        INSERT INTO model_diseases (id_model, id_disease, index_class)
        VALUES (%s, %s, %s)
    """
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            counter = 0
            for item in classes:
                cur.execute(sql, (id_model, item["id"], counter))
                counter += 1
            cnx.commit()
        return {"message": "All diseases inserted successfully"}
    finally:
        cnx.close()


def addModelFeaturesMapsModel(id_model: int, id_disease: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sql = """
        INSERT INTO model_features_maps (id_model, id_disease, name)
        VALUES (%s, %s, %s)
    """
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            for item in classes:
                cur.execute(sql, (id_model, id_disease, item["Feature"]))
            cnx.commit()
        return {"message": "All features maps inserted successfully"}
    finally:
        cnx.close()


def addModelSegmentationModel(id_model: int, id_biomarker: int) -> Dict[str, Any]:
    _execute(
        """
        INSERT INTO model_segmentation (id_model, id_biomarker)
        VALUES (%s, %s)
        """,
        (id_model, id_biomarker),
    )
    return {"message": "All stages inserted successfully"}


def addModelModel(data: Dict[str, Any], code: str, path: str, user: int) -> int:
    id_task = getTaskIdByKey(data["task"])
    input_size = f"{data['width']}x{data['height']}"
    return _execute(
        """
        INSERT INTO model
            (description, path_weights, input_size, active, datetime, id_task, code, id_model_base, id_user)
        VALUES
            (%s, %s, %s, 1, NOW(), %s, %s, %s, %s)
        """,
        (data["name"], path, input_size, id_task, code, data["model_base"], user),
    )


# ---------------------------
# Combos / catálogos
# ---------------------------

def getComboBaseModel() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_model_base, name FROM model_base ORDER BY id_model_base ASC"
    )


def getComboTasks() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT task_key AS id, name FROM task WHERE active=1 ORDER BY id_task ASC"
    )


def getComboFilter() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_filter_type AS id, name FROM filter_type ORDER BY id_filter_type ASC"
    )


def getComboObjectDetectionModel() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_model AS id, description AS name, 'Object Detection' AS title FROM model WHERE id_task = 4 ORDER BY id_model ASC"
    )


def getComboDiseases() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_disease AS id, name, 'Disease' AS title, id_region FROM diseases ORDER BY id_disease ASC"
    )


def getComboStages() -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT s.id_stage AS id, s.name, s.id_disease, 'Stage' AS title, d.id_region
        FROM stages s
        LEFT JOIN diseases d ON d.id_disease = s.id_disease
        ORDER BY s.id_stage ASC
        """
    )


def getComboBiomarkers() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_biomarker AS id, name, 'Biomarker' AS title, id_region FROM biomarkers ORDER BY id_biomarker ASC"
    )


def getComboModalities() -> List[Dict[str, Any]]:
    return _fetch_all(
        "SELECT id_modality, name, id_region FROM modalities ORDER BY id_modality ASC"
    )


def getModelsModelInfo() -> Dict[str, Any]:
    dataTasks, dataModalities, dataBaseModel, classification_diseases, classification_stages, classification_biomarkers, dataFilter, dataObjectDetection = (
        getComboTasks(),
        getComboModalities(),
        getComboBaseModel(),
        getComboDiseases(),
        getComboStages(),
        getComboBiomarkers(),
        getComboFilter(),
        getComboObjectDetectionModel(),
    )
    return {
        "dataTasks": dataTasks,
        "dataModalities": dataModalities,
        "dataBaseModel": dataBaseModel,
        "classification_diseases": classification_diseases,
        "classification_stages": classification_stages,
        "classification_biomarkers": classification_biomarkers,
        "dataFilter": dataFilter,
        "dataObjectDetection": dataObjectDetection,
    }


# ---------------------------
# Info por tipo (content)
# ---------------------------

def getInfoModelFeaturesMaps(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT mfm.id_model,
               'Layer Name' AS title,
               d.id_disease,
               d.name AS disease_name,
               mfm.name
        FROM model_features_maps mfm
        LEFT JOIN diseases d ON d.id_disease = mfm.id_disease
        WHERE mfm.id_model = %s
        """,
        (id_model,),
    )


def getInfoModelDiseases(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT md.id_model,
               'Disease' AS title,
               md.id_disease,
               d.name AS name,
               md.index_class
        FROM model_diseases md
        LEFT JOIN diseases d ON d.id_disease = md.id_disease
        WHERE md.id_model = %s
        """,
        (id_model,),
    )


def getInfoModelStages(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            ms.id_model,
            'Stage' AS title,
            ms.id_disease,
            d.name AS disease_name,
            ms.index_class,
            ms.id_stage,
            s.name AS name
        FROM model_stages ms
        LEFT JOIN stages s  ON s.id_stage = ms.id_stage
        LEFT JOIN diseases d ON d.id_disease = s.id_disease
        WHERE ms.id_model = %s
        """,
        (id_model,),
    )


def getInfoModelObjectDetection(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            modd.id_model,
            'Biomarker' AS title,
            modd.index_class,
            modd.id_biomarker,
            b.name AS name,
            b.biomarker_key,
            b.id_region,
            r.name AS region_name
        FROM model_object_detection modd
        LEFT JOIN biomarkers b ON modd.id_biomarker = b.id_biomarker
        LEFT JOIN regions r    ON r.id_region      = b.id_region
        WHERE modd.id_model = %s
        """,
        (id_model,),
    )


def getInfoModelSegmentation(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            ms.id_model,
            'Biomarker' AS title,
            ms.id_biomarker,
            b.name AS name,
            b.biomarker_key,
            b.id_region,
            r.name AS region_name
        FROM model_segmentation ms
        LEFT JOIN biomarkers b ON ms.id_biomarker = b.id_biomarker
        LEFT JOIN regions r    ON r.id_region     = b.id_region
        WHERE ms.id_model = %s
        """,
        (id_model,),
    )


def getInfoModelBiomarkers(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            mb.id_model,
            'Biomarker' AS title,
            mb.id_disease,
            d.name AS disease_name,
            mb.index_class,
            mb.id_biomarker,
            b.name AS name,
            b.biomarker_key,
            b.id_region,
            r.name AS region_name
        FROM model_biomarkers mb
        LEFT JOIN biomarkers b ON mb.id_biomarker = b.id_biomarker
        LEFT JOIN regions r    ON r.id_region     = b.id_region
        LEFT JOIN diseases d   ON d.id_disease    = mb.id_disease
        WHERE mb.id_model = %s
        """,
        (id_model,),
    )


# ---------------------------
# Estadísticas / Imágenes
# ---------------------------

def getStatisticsModelDiseases(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT 
            d.name AS name,
            COALESCE(COUNT(dd.id_detection_disease), 0) AS total_summary
        FROM model_diseases md
        LEFT JOIN model m ON m.id_model = md.id_model
        LEFT JOIN detection_diseases dd 
            ON dd.id_model_disease = md.id_model_disease AND dd.summary = 1
        LEFT JOIN diseases d ON d.id_disease = md.id_disease
        WHERE m.id_model = %s
        GROUP BY md.id_model_disease

        UNION ALL

        SELECT 
            'TOTAL' AS name,
            COUNT(dd.id_detection_disease) AS total_summary
        FROM model_diseases md
        LEFT JOIN model m ON m.id_model = md.id_model
        LEFT JOIN detection_diseases dd 
            ON dd.id_model_disease = md.id_model_disease AND dd.summary = 1
        WHERE m.id_model = %s
        """,
        (id_model, id_model),
    )


def getStatisticsPredictionModels(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT
            SUM(CASE WHEN is_correct = 1  THEN 1 ELSE 0 END) AS correct_count,
            SUM(CASE WHEN is_correct = 0  THEN 1 ELSE 0 END) AS incorrect_count,
            SUM(CASE WHEN is_correct = -1 THEN 1 ELSE 0 END) AS not_tested_count,
            COUNT(is_correct) AS count
        FROM detection_models dm
        WHERE dm.id_model = %s
        """,
        (id_model,),
    )


def getStatisticsModelStages(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT 
            s.name AS name,
            COALESCE(COUNT(ds.id_detection_stage), 0) AS total_summary
        FROM model_stages ms
        LEFT JOIN model m ON m.id_model = ms.id_model
        LEFT JOIN detection_stages ds 
            ON ds.id_model_stage = ms.id_model_stage AND ds.summary = 1
        LEFT JOIN stages s ON s.id_stage = ms.id_stage
        WHERE m.id_model = %s
        GROUP BY ms.id_model_stage

        UNION ALL

        SELECT 
            'TOTAL' AS id_model_stage,
            COUNT(*) AS total_summary_1
        FROM detection_stages
        WHERE summary = 1
        """,
        (id_model,),
    )


def getStatisticsModelBiomarkers(id_model: int) -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT 
            b.name AS name,
            COALESCE(COUNT(db.id_detection_biomarker), 0) AS total_summary
        FROM model_biomarkers mb
        LEFT JOIN model m ON m.id_model = mb.id_model
        LEFT JOIN detection_biomarkers db 
            ON db.id_model_biomarker = mb.id_model_biomarker AND db.summary = 1
        LEFT JOIN biomarkers b ON b.id_biomarker = mb.id_biomarker
        WHERE m.id_model = %s
        GROUP BY mb.id_model_biomarker

        UNION ALL

        SELECT 
            'TOTAL' AS id_model_biomarker,
            COUNT(*) AS total_summary_1
        FROM detection_biomarkers
        WHERE summary = 1
        """,
        (id_model,),
    )


def getImagesModelFeaturesMaps(id_model: int) -> List[Dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT dfm.id_detection_feature_map,
               dfm.id_detection_model,
               dfm.img,
               dfm.layer_name
        FROM detection_features_maps dfm
        LEFT JOIN model m ON m.id_model = dfm.id_model
        WHERE m.id_model = %s
        LIMIT 10
        """,
        (id_model,),
    )
    grouped: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        dm_id = row["id_detection_model"]
        if dm_id not in grouped:
            grouped[dm_id] = {"id_detection_model": dm_id, "images": []}
        grouped[dm_id]["images"].append(
            {
                "id_detection_feature_map": row["id_detection_feature_map"],
                "img": row["img"],
                "layer_name": row["layer_name"],
            }
        )
    return list(grouped.values())


def getImagesModelSegmentation(id_model: int) -> List[Dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT dsi.id_detection_segmentation_image,
               ds.id_detection_model,
               dsi.img
        FROM detection_segmentations_images dsi
        LEFT JOIN detection_segmentations ds
            ON ds.id_detection_segmentation = dsi.id_detection_segmentation
        LEFT JOIN model m ON m.id_model = ds.id_model
        WHERE dsi.id_type_image_segmentation = 2
          AND m.id_model = %s
        LIMIT 10
        """,
        (id_model,),
    )
    grouped: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        dm_id = row["id_detection_model"]
        if dm_id not in grouped:
            grouped[dm_id] = {"id_detection_model": dm_id, "images": []}
        grouped[dm_id]["images"].append(
            {
                "id_detection_segmentation_image": row["id_detection_segmentation_image"],
                "img": row["img"],
            }
        )
    return list(grouped.values())


# ---------------------------
# Dispatcher de dataContent
# ---------------------------

def getInfoModelContent(id_model: int, task_key: Optional[str]) -> Dict[str, Any]:
    if not task_key:
        return {}

    if task_key == "features_maps":
        return {
            "content": getInfoModelFeaturesMaps(id_model),
            "hardware": getInfoModelFeatureMapsServer(id_model),
            "images": getImagesModelFeaturesMaps(id_model),
        }
    if task_key == "classification_diseases":
        return {
            "content": getInfoModelDiseases(id_model),
            "hardware": getInfoModelDiseasesServer(id_model),
            "images": getStatisticsModelDiseases(id_model),
            "predictions": getStatisticsPredictionModels(id_model),
        }
    if task_key == "classification_stages":
        return {
            "content": getInfoModelStages(id_model),
            "hardware": getInfoModelStagesServer(id_model),
            "images": getStatisticsModelStages(id_model),
            "predictions": getStatisticsPredictionModels(id_model),
        }
    if task_key == "object_detection":
        return {
            "content": getInfoModelObjectDetection(id_model),
        }
    if task_key == "segmentation":
        return {
            "content": getInfoModelSegmentation(id_model),
            "hardware": getInfoModelSegmentationServer(id_model),
            "images": getImagesModelSegmentation(id_model),
        }
    if task_key == "classification_biomarkers":
        return {
            "content": getInfoModelBiomarkers(id_model),
            "hardware": getInfoModelBiomarkersServer(id_model),
            "images": getStatisticsModelBiomarkers(id_model),
            "predictions": getStatisticsPredictionModels(id_model),
        }
    return {}


def getModelsList(param: List[int], search: Optional[str] = None) -> Dict[str, Any]:
    """
    param = [limit, offset]
    search: texto opcional para filtrar por múltiples columnas.
    """
    limit, offset = param
    where_sql = ""
    args: List[Any] = []

    if search:
        like = f"%{search}%"
        where_sql = """
        WHERE
            m.description LIKE %s OR
            m.code        LIKE %s OR
            u.name        LIKE %s OR
            t.name        LIKE %s OR
            t.task_key    LIKE %s OR
            tc.name       LIKE %s OR
            moda.name     LIKE %s OR
            a.name        LIKE %s OR
            f.name        LIKE %s OR
            r.name        LIKE %s
        """
        args.extend([like, like, like, like, like, like, like, like, like, like])

    sql = f"""
        SELECT 
            m.id_model, 
            m.description                 AS name, 
            m.input_size,
            m.path_weights                AS path, 
            m.id_task, 
            m.id_target_category,
            tc.name                       AS target_category_name,
            m.active, 
            m.id_model_base, 
            mb.name                       AS model_base_name, 
            m.datetime, 
            m.id_user, 
            u.name                        AS user_name,
            mb.id_arquitecture,
            mb.id_framework, 
            a.name                        AS arquitecture_name, 
            f.name                        AS framework_name,
            mm.id_modality,
            moda.name                     AS modality_name,
            m.code,
            t.task_key,
            t.name                        AS task_name,
            r.name                        AS region_name,
            CASE WHEN myp.id_model IS NOT NULL THEN 1 ELSE 0 END AS has_yolo_preprocessor,
            CASE WHEN mf.id_model  IS NOT NULL THEN 1 ELSE 0 END AS has_filter
        FROM model m 
        LEFT JOIN task                   t    ON m.id_task = t.id_task 
        LEFT JOIN target_category        tc   ON m.id_target_category = tc.id_target_category
        LEFT JOIN model_base             mb   ON mb.id_model_base = m.id_model_base 
        LEFT JOIN users                  u    ON u.id_user = m.id_user 
        LEFT JOIN arquitectures          a    ON a.id_arquitecture = mb.id_arquitecture 
        LEFT JOIN frameworks             f    ON f.id_framework = mb.id_framework 
        LEFT JOIN model_modalities       mm   ON mm.id_model = m.id_model 
        LEFT JOIN model_yolo_preprocessor myp ON myp.id_model = m.id_model 
        LEFT JOIN model_filter_image     mf   ON mf.id_model = m.id_model
        LEFT JOIN modalities             moda ON moda.id_modality = mm.id_modality 
        LEFT JOIN regions                r    ON r.id_region = moda.id_region 
        {where_sql}
        ORDER BY m.id_model DESC
        LIMIT %s OFFSET %s
    """
    print(sql)

    args.extend([limit, offset])

    rows = _fetch_all(sql, tuple(args))
    if not rows:
        return {"modelDetails": [], "dataContent": []}

    model = rows[0]
    data_content = getInfoModelContent(model["id_model"], model.get("task_key"))
    return {"modelDetails": rows, "dataContent": data_content}
def getModelsDetailsModelInfo(code: Optional[str]) -> Dict[str, Any]:
    where = " WHERE m.code = %s" if code else ""
    params: List[Any] = [code] if code else []

    sql = f"""
        SELECT 
            m.id_model, 
            m.description                 AS name, 
            m.input_size,
            m.path_weights                AS path, 
            m.id_task, 
            m.id_target_category,
            tc.name           AS target_category_name,
            m.active, 
            m.id_model_base, 
            mb.name                       AS model_base_name, 
            m.datetime, 
            m.id_user, 
            u.name                        AS user_name,
            mb.id_arquitecture,
            mb.id_framework, 
            a.name                        AS arquitecture_name, 
            f.name                        AS framework_name,
            mm.id_modality,
            moda.name                     AS modality_name,
            m.code,
            t.task_key,
            t.name                        AS task_name,
            r.name                        AS region_name,

            CASE WHEN myp.id_model IS NOT NULL THEN 1 ELSE 0 END AS has_yolo_preprocessor,
            CASE WHEN mf.id_model  IS NOT NULL THEN 1 ELSE 0 END AS has_filter

        FROM model m 
        LEFT JOIN task                  t   ON m.id_task = t.id_task 
        LEFT JOIN target_category             tc   ON m.id_target_category       = tc.id_target_category
        LEFT JOIN model_base            mb  ON mb.id_model_base = m.id_model_base 
        LEFT JOIN users                 u   ON u.id_user = m.id_user 
        LEFT JOIN arquitectures         a   ON a.id_arquitecture = mb.id_arquitecture 
        LEFT JOIN frameworks            f   ON f.id_framework = mb.id_framework 
        LEFT JOIN model_modalities      mm  ON mm.id_model = m.id_model 
        LEFT JOIN model_yolo_preprocessor myp ON myp.id_model = m.id_model 
        LEFT JOIN model_filter_image    mf  ON mf.id_model = m.id_model
        LEFT JOIN modalities            moda ON moda.id_modality = mm.id_modality 
        LEFT JOIN regions               r    ON r.id_region = moda.id_region 
        {where}
        ORDER BY m.id_model DESC
    """

    rows = _fetch_all(sql, tuple(params))
    if not rows:
        return {"modelDetails": [], "dataContent": []}

    model = rows[0]
    data_content = getInfoModelContent(model["id_model"], model.get("task_key"))
    return {"modelDetails": rows, "dataContent": data_content}


def getModelsModelCards() -> List[Dict[str, Any]]:
    return _fetch_all(
        """
        SELECT m.id_model AS id, m.description AS name, mb.id_model_base AS id_model_base, m.code
        FROM model m
        LEFT JOIN model_base mb ON mb.id_model_base = m.id_model_base
        WHERE m.active = 1
        ORDER BY m.id_model DESC
        """
    )


def deleteModelModel(code: str, user: int) -> int:
    cnx = get_connection()
    try:
        with cnx.cursor() as cur:
            cur.execute(
                """
                UPDATE model
                SET active = 0, datetime = NOW(), id_user = %s
                WHERE code = %s
                """,
                (user, code),
            )
            cnx.commit()
            return cur.rowcount
    finally:
        cnx.close()
