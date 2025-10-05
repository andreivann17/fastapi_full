import numpy as np
import cv2
from tensorflow.keras.preprocessing.image import img_to_array, ImageDataGenerator
from keras.layers import BatchNormalization
from database.load_models import init_biomarkers_models_from_sql
import tensorflow as tf
import time
model_map = {}


# Monkey patch para aceptar lista en 'axis'
original_init = BatchNormalization.__init__
def patched_init(self, *args, **kwargs):
    if 'axis' in kwargs and isinstance(kwargs['axis'], list):
        kwargs['axis'] = kwargs['axis'][0]
    original_init(self, *args, **kwargs)
BatchNormalization.__init__ = patched_init

# Normalización
datagen = ImageDataGenerator(
    featurewise_center=True,
    featurewise_std_normalization=True,
)

def prepare_image(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224)) 
    img = img / 255.0  
    img = img_to_array(img)
    img = np.expand_dims(img, axis=0)
    img = datagen.standardize(img[0])  
    img = np.expand_dims(img, axis=0) 
    return img

def predict_image(img_path,id_disease, threshold=0.5):
    start_time = time.time()
    img = prepare_image(img_path)
    model = model_map[int(id_disease)]["model"]
    device = ""
    if tf.config.list_physical_devices('GPU'):
        print("✅ Se usará GPU")
        device = "GPU"
    else:
        print("⚠️ No hay GPU disponible, se usará CPU")
        device = "CPU"
    preds = model.predict(img)[0]  # shape: (4,)
    inference_time = round((time.time() - start_time) * 1000, 2)  # milisegundos

    activated = [i for i, p in enumerate(preds) if p >= threshold]
    summary_results = ["0"] * len(preds)
    for value in activated:
        summary_results[value] = "1"
    return {
        "device":device,
        "id_model":model_map[int(id_disease)]["id_model"],
         "biomarkers": model_map[int(id_disease)]["biomarkers"],
        "summary":summary_results,
        "predicted_labels": activated,
        "vector_probs": preds.tolist(),
        "time_inference": inference_time  # en milisegundos

    }



def __main__():
    global model_map
    model_map = init_biomarkers_models_from_sql()
__main__()
"""
# 🔍 Ejemplo de uso
if __name__ == "__main__":
    path = r"f:\dataset\fundus\images\aptos\train_images_crop\0369f3efe69b.png"
    result = predict_image(path)
    print(result)


"""