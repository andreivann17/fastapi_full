from PIL import Image
import torch
import torch.nn.functional as F
import time
from transformers import ViTForImageClassification, ViTImageProcessor
from torchvision.transforms import Compose, Resize, ToTensor, Normalize

# ─── Ruta del modelo exportado ──────────────────────────────
MODEL_PATH = r"F:\codigo\uabc_llm\models\models\model_vit_diabetic_retinopathy"  # ← AJUSTA ESTA RUTA
model = ViTForImageClassification.from_pretrained(MODEL_PATH)
image_processor = ViTImageProcessor.from_pretrained(MODEL_PATH)
# ─── Cargar modelo y procesador ─────────────────────────────
model.eval()

# ─── Transforms coherentes con entrenamiento ────────────────
size = (image_processor.size["height"], image_processor.size["width"])
transform = Compose([
    Resize(size),
    ToTensor(),
    Normalize(mean=image_processor.image_mean, std=image_processor.image_std)
])

# ─── Diccionario de etiquetas (ajústalo según tu orden) ─────
stages = {
    "0": "mild",
    "1": "moderate",
    "2": "severe",
    "3": "proliferative"
}

def preprocess_image(image_path, image_processor, device):
    image = Image.open(image_path).convert('RGB')
    inputs = image_processor(images=image, return_tensors="pt")
    # Mover los tensores al dispositivo (CPU o GPU)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    return inputs

def predict_image(image_path):
    start_time = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Preprocesamiento
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(pixel_values=image_tensor)

    # Softmax para clasificación multiclase
    logits = outputs.logits
    probs = F.softmax(logits, dim=-1).squeeze().cpu().numpy()
    predicted_idx = logits.argmax(-1).item()

    summary = ["0"] * len(probs)
    summary[predicted_idx] = "1"

    return {
        "predicted_label": stages[str(predicted_idx)],
        "summary": summary,
        "vector_probs": probs.tolist(),
        "labels": stages,
        "device": "GPU" if torch.cuda.is_available() else "CPU",
        "time_inference": round((time.time() - start_time) * 1000, 2)
    }
