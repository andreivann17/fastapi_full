from PIL import Image
import torch
import torch.nn.functional as F
from database.load_models import init_diseases_models_from_sql
import time

model_map = {}

def preprocess_image(image_path, image_processor, device):
    image = Image.open(image_path).convert('RGB')
    inputs = image_processor(images=image, return_tensors="pt")
    # Mover los tensores al dispositivo (CPU o GPU)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    return inputs

def predict_image(image_path):
    start_time = time.time()

    # Detectar si hay GPU y seleccionar dispositivo
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Mover modelo al dispositivo
    model = model_map["model"].to(device)
    
    inputs = preprocess_image(image_path, model_map["image_processor"], device)

    if device == torch.device('cuda'):
        device_str = "GPU"
    else:
        device_str = "CPU"

    with torch.no_grad():
        outputs = model(**inputs)

    inference_time = round((time.time() - start_time) * 1000, 2)  # milisegundos

    logits = outputs.logits
    probs = F.softmax(logits, dim=-1)
    predicted_class_idx = logits.argmax(-1).item()
    summary_results = ["0"] * len(model.config.id2label)
    summary_results[predicted_class_idx] = "1"
    predicted_label = model.config.id2label[predicted_class_idx]

    return {
        "device": device_str,
        "predicted_label": predicted_label,
        "diseases": model_map["diseases"],
        "id_model": model_map["id_model"],
        "summary": summary_results,
        "id_disease": model_map["diseases"][predicted_class_idx]["id_disease"],
        "labels": model.config.id2label,
        "vector_probs": probs.squeeze().tolist(),
        "time_inference": inference_time  # en milisegundos
    }

def __main__():
    global model_map
    model_map = init_diseases_models_from_sql()
   

__main__()
