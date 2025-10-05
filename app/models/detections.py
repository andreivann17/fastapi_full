"""
Detection model functions.

This module encapsulates data access helpers for the detection workflow.
Functions here perform inserts into the various tables involved in
capturing a detection event and its downstream model results. The
implementation mirrors the Node.js code in ``models/detectionsModel.js``
but uses Python and ``mysql.connector``. A ``UserAgent`` parser is
used to derive browser and device metadata from the request.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from user_agents import parse as parse_user_agent

from ..db import get_connection


def _get_server_type_id(device_name: str) -> int:
    """Look up the ``server_type`` identifier for a given device name.

    Args:
        device_name: The human‑readable name of the device (e.g.
            ``"cpu"``, ``"gpu"``). The lookup is case‑insensitive and
            matches against the ``components_hardware.name`` column.

    Returns:
        The ``id_server_type`` associated with the component. If no
        matching row is found a ``ValueError`` is raised.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT st.id_server_type
                FROM server_type st
                LEFT JOIN components_hardware ch ON ch.id_component_hardware = st.id_component_hardware
                WHERE LOWER(ch.name) = LOWER(%s)
                LIMIT 1
                """,
                (device_name,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No server_type found for device {device_name}")
            return row[0]
    finally:
        conn.close()


def insert_detection(
    patient_id: int,
    img_path: str,
    code: str,
    user_agent_str: str,
    ip_public: str,
) -> int:
    """Insert a detection row and return its primary key.

    Args:
        patient_id: Foreign key into ``patients``.
        img_path: Path to the uploaded image file on disk.
        code: Unique identifier used to group downstream data.
        user_agent_str: Raw User‑Agent header from the client.
        ip_public: The public IP address of the client.

    Returns:
        The ``id_detection`` inserted.
    """
    ua = parse_user_agent(user_agent_str or "")
    browser_name = ua.browser.family or None
    device_type = ("mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop")
    os_name = ua.os.family or None
    os_version = ua.os.version_string or None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detections (
                    id_patient, img, code, active, datetime,
                    browser_name, device_type, os_name, os_version, ip_public
                )
                VALUES (%s, %s, %s, 1, NOW(), %s, %s, %s, %s, %s)
                """,
                (
                    patient_id,
                    img_path,
                    code,
                    browser_name,
                    device_type,
                    os_name,
                    os_version,
                    ip_public,
                ),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def insert_detection_model(
    id_detection: int,
    id_task: int,
    time_inference: float,
    device: str,
    id_model: int,
) -> int:
    """Insert a row into ``detection_models`` and return its ID."""
    id_server_type = _get_server_type_id(device)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_models (
                    id_detection, id_task, time_inference, is_correct, id_server_type, id_model
                )
                VALUES (%s, %s, %s, '-1', %s, %s)
                """,
                (id_detection, id_task, time_inference, id_server_type, id_model),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def insert_detection_disease(
    id_detection_model: int,
    id_model_disease: int,
    score: float,
    summary: str,
) -> int:
    """Insert a row into ``detection_diseases`` and return its ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_diseases (id_detection_model, id_model_disease, score, summary)
                VALUES (%s, %s, %s, %s)
                """,
                (id_detection_model, id_model_disease, score, summary),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def insert_detection_biomarker(
    id_detection_model: int,
    id_model_biomarker: int,
    score: float,
    summary: str,
    id_detection_model_disease: int,
) -> None:
    """Insert a biomarker result row."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_biomarkers (
                    id_detection_model, id_model_biomarker, score, summary, id_detection_model_disease
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_detection_model, id_model_biomarker, score, summary, id_detection_model_disease),
            )
            conn.commit()
    finally:
        conn.close()


def insert_detection_stage(
    id_detection_model: int,
    id_model_stage: int,
    score: float,
    summary: str,
    id_detection_model_disease: int,
) -> None:
    """Insert a stage result row."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_stages (
                    id_detection_model, id_model_stage, score, summary, id_detection_model_disease
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (id_detection_model, id_model_stage, score, summary, id_detection_model_disease),
            )
            conn.commit()
    finally:
        conn.close()


def insert_detection_segmentation(
    id_detection_model: int,
    id_model: int,
    id_detection_model_disease: int,
) -> int:
    """Insert a segmentation result parent row and return its ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_segmentations (
                    id_detection_model, id_model, id_detection_model_disease
                )
                VALUES (%s, %s, %s)
                """,
                (id_detection_model, id_model, id_detection_model_disease),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def insert_detection_segmentation_image(
    id_detection_segmentation: int,
    img_path: str,
    is_full_image_mask: int,
    id_type_image_segmentation: int,
) -> None:
    """Insert a segmentation image result row."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_segmentations_images (
                    id_detection_segmentation, img, is_full_image_mask, id_type_image_segmentation
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    id_detection_segmentation,
                    img_path,
                    is_full_image_mask,
                    id_type_image_segmentation,
                ),
            )
            conn.commit()
    finally:
        conn.close()


def insert_detection_feature_map(
    id_detection_model: int,
    layer_name: str,
    img_path: str,
    id_detection_model_disease: int,
    id_model: int,
) -> None:
    """Insert a feature map result row."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO detection_features_maps (
                    layer_name, img, id_detection_model, id_detection_model_disease, id_model
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (layer_name, img_path, id_detection_model, id_detection_model_disease, id_model),
            )
            conn.commit()
    finally:
        conn.close()
