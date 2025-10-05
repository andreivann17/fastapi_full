"""
Detection endpoints.

This router exposes an endpoint for inserting a new detection. The
client uploads an image and the server stores it on disk, inserts a
row into the ``detections`` table and optionally runs inference
models. The inference portion is simplified compared to the original
Node.js implementation: only disease classification is performed
through the ViT model in ``tasks.diseases_ViT``. Additional tasks
such as segmentation, feature maps and biomarker detection can be
integrated following the same pattern.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from ..deps import get_current_user
from ..models import detections as det_model
from ..models import records as records_model  # For future integration

try:
    # Import tasks lazily; tasks may rely on heavy ML libraries.
    from ..tasks import diseases_ViT
except ImportError:
    diseases_ViT = None

router = APIRouter(prefix="/detections", tags=["detections"])


class DetectionResponse(BaseModel):
    ok: bool
    imagePath: str
    code: str
    results: Dict[str, Any]


@router.post("/insert", response_model=DetectionResponse)
async def insert_detection_route(
    request: Request,
    img: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DetectionResponse:
    """Handle a new detection upload.

    1. Save the uploaded image under ``uploads/detections/original/{code}/original.jpg``.
    2. Insert a row into the ``detections`` table with metadata from the
       User‑Agent and client IP.
    3. Run disease classification using the ViT model and store its
       results in ``detection_models`` and ``detection_diseases``.

    Returns:
        A ``DetectionResponse`` containing the code and minimal results.
    """
    # Generate code by stripping hyphens from a UUID
    code = uuid.uuid4().hex
    # Prepare directories
    base_original = os.path.join(os.getcwd(), "uploads", "detections", "original", code)
    base_segmentation = os.path.join(os.getcwd(), "uploads", "detections", "segmentation", code)
    base_features = os.path.join(os.getcwd(), "uploads", "detections", "features_maps", code)
    for path in [base_original, base_segmentation, base_features]:
        os.makedirs(path, exist_ok=True)
    # Save original image
    image_path = os.path.join(base_original, "original.jpg")
    content = await img.read()
    with open(image_path, "wb") as f:
        f.write(content)
    # Insert detection row
    user_agent = request.headers.get("user-agent", "")
    ip_public = request.client.host or ""
    id_detection = det_model.insert_detection(
        patient_id=current_user.get("id"),
        img_path=image_path,
        code=code,
        user_agent_str=user_agent,
        ip_public=ip_public,
    )
    # Prepare response container
    results: Dict[str, Any] = {}
    # Run disease classification if available
    if diseases_ViT is not None:
        try:
            disease_res = diseases_ViT.predict_image(image_path)
            # Insert detection_models row (task id 1 used for diseases)
            det_model_id = det_model.insert_detection_model(
                id_detection=id_detection,
                id_task=1,
                time_inference=disease_res.get("time_inference", 0.0),
                device=disease_res.get("device", "CPU"),
                id_model=disease_res.get("id_model", 0),
            )
            # Insert detection_diseases row
            id_model_disease = disease_res.get("id_model")
            score_vector = disease_res.get("vector_probs")
            summary = disease_res.get("summary")
            # Iterate over diseases list from tasks
            diseases = disease_res.get("diseases", [])
            chart = []
            for idx, disease in enumerate(diseases):
                score = score_vector[idx] if score_vector and idx < len(score_vector) else 0.0
                summary_flag = summary[idx] if summary and idx < len(summary) else "0"
                # Insert row
                id_det_dis = det_model.insert_detection_disease(
                    id_detection_model=det_model_id,
                    id_model_disease=disease.get("id_model_disease", 0),
                    score=score,
                    summary=summary_flag,
                )
                chart.append({"name": disease.get("name"), "score": score, "summary": summary_flag})
            results = {"predicted_label": disease_res.get("predicted_label"), "chart": chart}
        except Exception as exc:
            # Log the error but continue; inference is optional
            print(f"Error running disease inference: {exc}")
    return DetectionResponse(ok=True, imagePath=image_path, code=code, results=results)
