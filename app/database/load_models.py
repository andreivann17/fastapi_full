
from transformers import ViTForImageClassification, ViTImageProcessor
from database.database import get_connection 
import tensorflow as tf
from ultralytics import YOLO
import torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
import os

def find_model_file(folder_path, framework):
    full_dir = os.path.join("../hanei/backend", folder_path)
    if not os.path.isdir(full_dir):
        return None
    
    files = os.listdir(full_dir)

    if framework == "transformers":
        for f in files:
            if f == "config.json":
                return full_dir  # Huggingface carga desde carpeta
    elif framework == "tensorflow":
        for f in files:
            if f.endswith(".h5") or f.endswith(".keras"):
                return os.path.join(full_dir, f)
    elif framework == "torch":
        for f in files:
            if f.endswith(".pt") or f.endswith(".pth"):
                return os.path.join(full_dir, f)
    elif framework == "onnx":
        for f in files:
            if f.endswith(".onnx"):
                return os.path.join(full_dir, f)
    return None

def is_folder(path):
    return os.path.isdir(os.path.join("../hanei/backend", path))
def init_diseases_models_from_sql():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
  SELECT 
    m.id_model AS id_model,
    ms.id_disease,
    ms.index_class,
    d.name AS name,
    ms.id_model_disease AS id_model_disease,
    
    -- Sustituimos los campos estáticos por EXISTS dinámicos
   EXISTS (
    SELECT 1
    FROM biomarkers_maligns bm
    JOIN model_segmentation ms ON bm.id_biomarker = ms.id_biomarker
    JOIN model m2 ON ms.id_model = m2.id_model
    WHERE bm.id_disease = d.id_disease
      AND m2.active = 1
      AND m2.id_task = 3
)
AS is_segmentation,

    EXISTS (
        SELECT 1 FROM model m3 
        JOIN model_biomarkers mb ON m3.id_model = mb.id_model
        WHERE mb.id_disease = d.id_disease AND m3.id_task = 7 AND m3.active = 1
    ) AS is_biomarker,

    EXISTS (
        SELECT 1 FROM model m4 
        JOIN model_stages ms2 ON m4.id_model = ms2.id_model
        WHERE ms2.id_disease = d.id_disease AND m4.id_task = 6 AND m4.active = 1
    ) AS is_stage,

    EXISTS (
        SELECT 1 FROM model m5 
        JOIN model_features_maps mfm ON m5.id_model = mfm.id_model
        WHERE mfm.id_disease = d.id_disease AND m5.id_task = 2 AND m5.active = 1
    ) AS is_feature_map,

    d.health,
    m.path_weights AS path

FROM model m
LEFT JOIN model_diseases ms ON m.id_model = ms.id_model
RIGHT JOIN diseases d ON d.id_disease = ms.id_disease
WHERE m.active = 1 AND m.id_task = 1
ORDER BY ms.index_class ASC;
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No se encontraron modelos de enfermedad en la base de datos.")
        return

    path = rows[0]["path"]
    

    model_loaded = ViTForImageClassification.from_pretrained("../hanei/backend/"+path+"/model")
    image_processor = ViTImageProcessor.from_pretrained("../hanei/backend/"+path+"/model")


    model_info = {
        "path": path,
        "id_model": rows[0]["id_model"],
        "model": model_loaded,
        "image_processor": image_processor,
        "diseases": []
    }

    for row in rows:
        model_info["diseases"].append({
            "id_disease": row["id_disease"],
            "name": row["name"],
            "id_model_disease":row["id_model_disease"],
            "index_class": row["index_class"],
            "is_biomarker": row["is_biomarker"],
            "is_segmentation":row["is_segmentation"],
            "is_stage": row["is_stage"],
            "is_feature_map": row["is_feature_map"],
            "health": row["health"]
        })
    
    return model_info

def init_stages_models_from_sql():  
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
       SELECT 
           m.id_model as id_model,
           ms.id_disease as id_disease,
           ms.id_model_stage as id_model_stage,
           m.path_weights as path,
           s.name,
           s.id_stage as id_stage,
           ms.index_class 
        FROM model_stages ms 
        LEFT JOIN model m ON m.id_model = ms.id_model 
        LEFT JOIN stages s ON s.id_stage = ms.id_stage 
        WHERE m.active = 1 AND m.id_task = 6 
        ORDER BY ms.index_class ASC;
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No se encontraron modelos de enfermedad en la base de datos.")
        return

    # Agrupar por id_disease
    disease_models = {}
    model_cache = {}

    for row in rows:
        id_disease = row["id_disease"]
        path = row["path"]

        # Cargar solo una vez por path
        if path not in model_cache:
            model_path = find_model_file(path, "tensorflow")
            if not model_path:
                print("No se encontró modelo TensorFlow en:", path)
                continue
            model_loaded = tf.keras.models.load_model(model_path)

            
            model_cache[path] = {
                "model": model_loaded,
            
            }

        # Si no existe aún el id_disease en el diccionario, lo agregamos
        if id_disease not in disease_models:
            disease_models[id_disease] = {
                "path": path,
                "id_model": row["id_model"],
                "model": model_cache[path]["model"],
                "stages": []
            }

        # Agregar stage a la lista de stages del id_disease correspondiente
        disease_models[id_disease]["stages"].append({
            "id_stage": row["id_stage"],
            "id_model_stage":row["id_model_stage"],
            "index_class": row["index_class"],
        })
    
    return disease_models

def init_fm_models_from_sql():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
      SELECT 
           m.id_model as id_model,
           mfs.id_disease as id_disease,
           m.path_weights as path,
           mfs.name,
           mfs.id_model_feature_map as id_model_fm
      
        FROM model_features_maps mfs 
        LEFT JOIN model m ON m.id_model = mfs.id_model 
   
        WHERE m.active = 1 AND m.id_task = 2
        ORDER BY mfs.id_model_feature_map ASC;
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No se encontraron modelos de enfermedad en la base de datos.")
        return

    # Agrupar por id_disease
    disease_models = {}
    model_cache = {}

    for row in rows:
        id_disease = row["id_disease"]
        path = row["path"]

        # Cargar solo una vez por path
        if path not in model_cache:
            model_path = find_model_file(path, "tensorflow")
            if not model_path:
                print("No se encontró modelo TensorFlow en:", path)
                continue
            model_loaded = tf.keras.models.load_model(model_path)

            model_cache[path] = {
                "model": model_loaded,
            }

        # Si no existe aún el id_disease en el diccionario, lo agregamos
        if id_disease not in disease_models:
            disease_models[id_disease] = {
                "path": path,
                "id_model": row["id_model"],
                "model": model_cache[path]["model"],
                "layers": []
            }

        # Agregar stage a la lista de stages del id_disease correspondiente
        disease_models[id_disease]["layers"].append({
            "id_model_fm": row["id_model_fm"],
            "name": row["name"],
        })
   
    return disease_models

def init_segmentation_models_from_sql():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
SELECT 
    MAX(ms.id_model) AS id_model,
    MAX(m.description) AS description,
    ms.id_model_segmentation,
    b.id_biomarker,
    m.active,
    MAX(m.path_weights) AS path,
    MAX(b.biomarker_key) AS biomarker_key, 
    MAX(myp.class_detection) AS class_detection, 
    MAX(myp.id_model_required) AS id_model_ob,

    GROUP_CONCAT(DISTINCT bm.id_disease) AS id_disease,
    GROUP_CONCAT(DISTINCT d.name SEPARATOR ', ') AS disease_names,

    IF(COUNT(DISTINCT bm.id_disease) > 0, 1, 0) AS malign,

    CASE 
        WHEN MAX(myp.id_model) IS NOT NULL AND MAX(m2.active) = 1 THEN TRUE 
        ELSE FALSE 
    END AS is_yolo,

    CASE 
        WHEN MAX(mfi.id_model) IS NOT NULL AND MAX(m3.active) = 1 THEN MAX(ft.filter_key) 
        ELSE -1
    END AS is_filter

FROM model_segmentation ms 
LEFT JOIN model m ON m.id_model = ms.id_model
LEFT JOIN model_yolo_preprocessor myp ON myp.id_model = ms.id_model
LEFT JOIN model_filter_image mfi ON mfi.id_model = ms.id_model
LEFT JOIN filter_type ft ON mfi.id_filter_type = ft.id_filter_type
LEFT JOIN biomarkers b ON b.id_biomarker = ms.id_biomarker
LEFT JOIN biomarkers_maligns bm ON b.id_biomarker = bm.id_biomarker
LEFT JOIN diseases d ON d.id_disease = bm.id_disease
LEFT JOIN model m2 ON m2.id_model = myp.id_model
LEFT JOIN model m3 ON m3.id_model = mfi.id_model
where m.active = 1
GROUP BY ms.id_model_segmentation;
    """)
    rows = cursor.fetchall()
    conn.close()
    model_map = {}
    for row in rows:
        if len(row["path"]) > 0:
            model_path = find_model_file(row["path"], "torch")
            if not model_path:
                continue
            model_loaded = torch.load(model_path, map_location=device)

            model_loaded.to(device)
            model_loaded.eval()

            # Separar las enfermedades en arrays
            id_diseases = str(row["id_disease"]).split(",") if row["id_disease"] else []
            disease_names = str(row["disease_names"]).split(", ") if row["disease_names"] else []

            # Armar el subarray de enfermedades
            diseases_array = []
            for i in range(min(len(id_diseases), len(disease_names))):
                diseases_array.append({
                    "id_disease": id_diseases[i],
                    "name": disease_names[i]
                })

            model_map[row["id_biomarker"]] = {
                "model": model_loaded,
                "biomarker_key": str(row["biomarker_key"]),
                "id_model": str(row["id_model"]),
                "id_model_segmentation": str(row["id_model_segmentation"]),
                "id_biomarker": str(row["id_biomarker"]),
                "malign": str(row["malign"]),
                "is_yolo": str(row["is_yolo"]),
                "id_model_ob": str(row["id_model_ob"]),
                "class_detection": [str(row["class_detection"])],
                "diseases": diseases_array  # ✅ subarray de enfermedades
            }
    return model_map


def init_od_models_from_sql():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
SELECT 
    m.id_model AS id_model,
    m.path_weights AS path,
    modd.id_biomarker,
    modd.index_class,
    b.name
FROM model m
LEFT JOIN model_object_detection modd ON m.id_model = modd.id_model
LEFT JOIN biomarkers b ON b.id_biomarker = modd.id_biomarker
WHERE m.active = 1 AND m.id_task = 4;
    """)
    rows = cursor.fetchall()
    conn.close()

    model_yolo_map = {}
    model_cache = {}

    for row in rows:
        id_model = str(row["id_model"])
        path = row["path"]

        if path not in model_cache:
            model_path = find_model_file(path, "onnx")
            if not model_path:
                continue
            model_cache[path] = YOLO(model_path)


        if id_model not in model_yolo_map:
            model_yolo_map[id_model] = {
                "model": model_cache[path],
                "path": path,
                
                "id_model": str(row["id_model"]),
                "objects": []
            }

        model_yolo_map[id_model]["objects"].append({
            "id_biomarker": str(row["id_biomarker"]),
            "index_class": str(row["index_class"]),
            "name": row["name"]
        })

    return model_yolo_map

def init_biomarkers_models_from_sql():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            m.id_model as id_model,
            mb.id_model_biomarker as id_model_biomarker,
            mb.id_disease as id_disease,
            b.id_biomarker  as id_biomarker,
            m.path_weights as path,
            mb.index_class
        FROM model_biomarkers mb 
        LEFT JOIN model m ON m.id_model = mb.id_model 
        LEFT JOIN biomarkers b ON mb.id_biomarker  = b.id_biomarker  
        WHERE m.active = 1 AND m.id_task = 7;
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No se encontraron modelos de enfermedad en la base de datos.")
        return

    biomarker_models = {}
    model_cache = {}

    for row in rows:
        id_disease = row["id_disease"]
        path = row["path"]

        # Cargar modelo una sola vez por path
        if path not in model_cache:
            model_path = find_model_file(path, "tensorflow")
            if not model_path:
                print("No se encontró modelo TensorFlow en:", path)
                continue
            model_loaded = tf.keras.models.load_model(model_path)
            model_cache[path] = model_loaded

        # Si la enfermedad aún no se ha agregado, iniciarla
        if id_disease not in biomarker_models:
            biomarker_models[id_disease] = {
                "path": path,
                "id_model": row["id_model"],
                "model": model_cache[path],
                "biomarkers": []
            }

        # Agregar el biomarcador
        biomarker_models[id_disease]["biomarkers"].append({
            "id_biomarker": row["id_biomarker"],
            "id_model_biomarker":row["id_model_biomarker"],
            "index_class": row["index_class"]
        })
  

    return biomarker_models