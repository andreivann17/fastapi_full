from transformers import BeitForImageClassification, BeitImageProcessor
import torch
from PIL import Image
from torchvision.transforms import Compose, Resize, ToTensor, Normalize
import torch.nn.functional as F
import time
import os

# Ruta del folder exportado
MODEL_DIR = r"F:\codigo\uabc_llm\models\models\beit_dataset_fundus_biomarkers"  # ← AJUSTA ESTA RUTA

# ─── Cargar modelo y procesador ──────────────────────────────
model = BeitForImageClassification.from_pretrained(MODEL_DIR)
image_processor = BeitImageProcessor.from_pretrained(MODEL_DIR)
model.eval()

# ─── Transformaciones iguales al entrenamiento ───────────────
size = (image_processor.size["height"], image_processor.size["width"])
transform = Compose([
    Resize(size),
    ToTensor(),
    Normalize(mean=image_processor.image_mean, std=image_processor.image_std)
])

# ─── Diccionario de labels (ajústalo tú mismo) ───────────────
biomarkers = {
    "0": "exudados duros",
    "1": "hemorragias",
    "2": "laser spot",
    "3": "microaneurismas",
    "4": "tessellated",
    "5": "choroidal",
    "6": "patchy",
    "7": "patologia myopia",
    "8": "diabetic retinopathy",
    "9": "cataract",
    "10": "normal"
}

# Diccionario de etiquetas (ajústalo a tu orden real)
biomarkers = {
    "0": "exudados duros",
    "1": "hemorragias",
    "2": "laser spot",
    "3": "microaneurismas",
    "4": "tessellated",
    "5": "choroidal",
    "6": "patchy",
    "7": "patologia myopia",
    "8": "diabetic retinopathy",
    "9": "cataract",
    "10": "normal"
}

def predict_image(image_path, threshold=0.5):
    start_time = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Preprocesar imagen
    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image).unsqueeze(0).to(device)

    # Inferencia
    with torch.no_grad():
        outputs = model(pixel_values=image_tensor)

    # Activaciones
    probs = torch.sigmoid(outputs.logits).squeeze().cpu().numpy()
    activated = [i for i, p in enumerate(probs) if p >= threshold]
    summary = ["0"] * len(probs)
    for i in activated:
        summary[i] = "1"

    biomarker_names = [biomarkers[str(i)] for i in activated]

    return {
        "predicted_labels": activated,
        "biomarker_names": biomarker_names,
        "summary": summary,
        "vector_probs": probs.tolist(),
        "labels": biomarkers,
        "device": "GPU" if torch.cuda.is_available() else "CPU",
        "time_inference": round((time.time() - start_time) * 1000, 2)
    }

