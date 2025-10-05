import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import SamProcessor, SamConfig
import torch
import torch.nn.functional as F
import os
from util.ben_filter import process_ben_image 
from util.util import crear_carpeta, extraer_pixeles_blancos_reales, transparent_image
from database.load_models import init_segmentation_models_from_sql,init_od_models_from_sql
import time



model_config = SamConfig.from_pretrained("facebook/sam-vit-base")
processor = SamProcessor.from_pretrained("facebook/sam-vit-base")

model_map = {}
model_yolo_map = {}
results_yolo_cache = {}

def format_bounding_box(bounding_box):
    return [[bounding_box[0], bounding_box[1], bounding_box[2], bounding_box[3]]]

def detect_yolo(image_path, image_id, id_model_ob):
    if id_model_ob in results_yolo_cache:
        return results_yolo_cache[id_model_ob]

    yolo_model = model_yolo_map[str(id_model_ob)]['model']
    img = Image.open(image_path).convert('RGB').resize((640, 640))
    img_np = np.array(img)
    im2_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
    results = yolo_model.predict(source=[im2_rgb], name=image_id, save=True, save_txt=True, project="../hanei/backend/uploads/detections/objectDetection")

    results_yolo_cache[id_model_ob] = results
    return results

def get_bounding_boxes(yolo_class, results):
    detections = results[0].boxes.xyxy.cpu().numpy()
    classes = results[0].boxes.cls.cpu().numpy()
    filtered = detections[np.isin(classes, yolo_class)]

    if len(filtered) == 0:
        return None

    scale_factor = 256 / 640
    boxes = []
    for det in filtered:
        x_min, y_min, x_max, y_max = det[:4] * scale_factor
        boxes.append([max(0, min(256, x_min)), max(0, min(256, y_min)), max(0, min(256, x_max)), max(0, min(256, y_max))])
    return boxes

def process_images(image_path_original, image_path_ben, baseSegmentationPath, config, results_yolo):
    crear_carpeta(baseSegmentationPath, config["biomarker_key"])
    start_time = time.time()
    model = config['model']
    yolo_class = config['class_detection']
    id_model = config['id_model']
    id_biomarker = config['id_biomarker']
    img = Image.open(image_path_ben).convert('RGB').resize((256, 256))
    img_np = np.array(img)
    height, width = img_np.shape[:2]
    prompts = get_bounding_boxes(yolo_class, results_yolo) if (config['is_yolo'] == "0") and results_yolo else None
    formatted = [format_bounding_box(b) for b in prompts] if prompts else [[[0.0, 0.0, float(width), float(height)]]]
    combined_mask = np.zeros((height, width), dtype=np.uint8)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    for prompt in formatted:
        inputs = processor(img_np, input_boxes=[prompt], return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        model.eval()
        with torch.no_grad():
            out = model(**inputs, multimask_output=False)

        pred = torch.sigmoid(out.pred_masks.squeeze(1)).cpu().numpy().squeeze()
        pred_resized = F.interpolate(torch.tensor(pred).unsqueeze(0).unsqueeze(0), size=(height, width), mode='nearest').squeeze().numpy()
        bin_mask = (pred_resized > 0.5).astype(np.uint8)
        combined_mask = np.maximum(combined_mask, bin_mask)

    inference_time = round((time.time() - start_time) * 1000, 2)
    combined_mask = np.where(combined_mask > 0.5, 255, 0).astype(np.uint8)
    save_base = os.path.join(baseSegmentationPath, config["biomarker_key"])
    binary_path = f"{save_base}/binary_mask.png"
    real_path = f"{save_base}/real.png"
    transparent_path = f"{save_base}/transparent.png"

    if device == 'cuda':
        device = "gpu"
    device_str = str(device).upper()
    cv2.imwrite(binary_path, combined_mask)
    extraer_pixeles_blancos_reales(real_path, image_path_original, binary_path)
    transparent_image(transparent_path, binary_path)
    binary_path = binary_path.replace("../hanei/backend/", "")
    transparent_path = transparent_path.replace("../hanei/backend/", "")
    real_path = real_path.replace("../hanei/backend/", "")
    print(binary_path)
 

    return {
        "device":device_str,
        "time_inference": inference_time,
        "id_model": id_model,
        "id_biomarker": id_biomarker,
        "biomarker_key": config["biomarker_key"],
        "id_model_segmentation": config["id_model_segmentation"],
        "segmented_pixels_count": int(np.sum(combined_mask)),
        "paths": [
            {"path": binary_path, "is_full_image_mask": "1","id_type_image_segmentation":"1"},
            {"path": real_path, "is_full_image_mask": "1","id_type_image_segmentation":"2"},
            {"path": transparent_path, "is_full_image_mask": "1","id_type_image_segmentation":"3"}
        ]
    }
def preprocess_images2(image_id, image_path, baseImagePath, baseSegmentationPath):
    results = []
    directory_ben = process_ben_image("../hanei/backend/" + image_path, "../hanei/backend/" + baseImagePath)

    used_yolo_results = {}

    for key, conf in model_yolo_map.items():
        id_model_ob = conf['id_model']

        if id_model_ob not in used_yolo_results:
            used_yolo_results[id_model_ob] = detect_yolo("../hanei/backend/" + image_path, image_id, id_model_ob)

        try:
            result = process_images(
                "../hanei/backend/" + image_path,
                directory_ben,
                "../hanei/backend/" + baseSegmentationPath,
                conf['id_biomarker'],
                conf,
                used_yolo_results[id_model_ob]
            )
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})

    return results

def preprocess_images(image_id, image_path, baseImagePath, baseSegmentationPath, id_disease):
    results = []

    directory_ben = process_ben_image(
        "../hanei/backend/" + image_path,
        "../hanei/backend/" + baseImagePath
    )

    used_yolo_results = {}

    with ThreadPoolExecutor() as executor:
        futures = []

        # 🔍 Filtrado según condición
        if id_disease == "-1":
            new_model_map = {
                key: config for key, config in model_map.items()
                if config.get("malign") == "0"
            }
        else:
            new_model_map = {
                key: config for key, config in model_map.items()
                if config.get("malign") == "1" and any(
                    str(d.get("id_disease")) == str(id_disease)
                    for d in config.get("diseases", [])
                )
            }

        for key, config in new_model_map.items():
            id_model_ob = config.get("id_model_ob")
            is_yolo = config.get("is_yolo", "0")

            if is_yolo == "1" and id_model_ob not in used_yolo_results:
                used_yolo_results[id_model_ob] = detect_yolo(
                    "../hanei/backend/" + image_path,
                    image_id,
                    id_model_ob
                )

            results_yolo = used_yolo_results.get(id_model_ob, [])

            futures.append(executor.submit(
                process_images,
                "../hanei/backend/" + image_path,
                directory_ben,
                "../hanei/backend/" + baseSegmentationPath,
                config,
                results_yolo
            ))

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append({"error": str(e)})

    return results


def __main__():
    global model_map
    global model_yolo_map
    model_map= init_segmentation_models_from_sql()
    model_yolo_map = init_od_models_from_sql()
    print(model_map)
__main__()