from PIL import Image
import torch
import torch.nn.functional as F
from database.load_models import init_stages_models_from_sql

model_map = {}

def preprocess_image(image_path,image_processor):
    image = Image.open(image_path).convert('RGB')
    inputs = image_processor(images=image, return_tensors="pt")
    return inputs

def predict_image(image_path,id_disease):
    print("-----")
    print(id_disease)
    inputs = preprocess_image(image_path,model_map[int(id_disease)]["image_processor"])
    model = model_map[int(id_disease)]["model"]
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    probs = F.softmax(logits, dim=-1)
    predicted_class_idx = logits.argmax(-1).item()
    summary_results = ["0"] * len(model.config.id2label)
    summary_results[predicted_class_idx] = "1"
    predicted_label = model.config.id2label[predicted_class_idx]
    return {"predicted_label":predicted_label,"id_model":model_map[int(id_disease)]["id_model"],"summary":summary_results,"labels":model.config.id2label,"vector_probs": probs.squeeze().tolist()}  # lista de probabilidades

def __main__():
    global model_map
    model_map = init_stages_models_from_sql()

__main__()
