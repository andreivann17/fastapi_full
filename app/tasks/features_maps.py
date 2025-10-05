import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
from tensorflow.keras.preprocessing.image import img_to_array, ImageDataGenerator
import cv2
import os
import time

from database.load_models import init_fm_models_from_sql
datagen = ImageDataGenerator(
    featurewise_center=True,
    featurewise_std_normalization=True,
)
model_map = {}
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

def get_connected_conv_layers(model, input_shape=(224,224,3)):
    connected_layers = []
    dummy_input = tf.zeros((1,) + input_shape)
    for layer in model.layers:
        if "conv" in layer.name.lower():
            try:
                submodel = tf.keras.Model(inputs=model.input, outputs=layer.output)
                _ = submodel(dummy_input)
                connected_layers.append(layer)
            except:
                pass
    return connected_layers

def create_feature_extractor(model, connected_layers):
    outputs = [layer.output for layer in connected_layers]
    feature_extractor = tf.keras.Model(inputs=model.input, outputs=outputs)
    return feature_extractor

def visualize_feature_maps(img_path, output_dir,id_disease):
    start_time = time.time()
    img = prepare_image(img_path)
    os.makedirs(output_dir, exist_ok=True)
    

    connected_conv_layers = get_connected_conv_layers(model_map[int(id_disease)]["model"])

    if not connected_conv_layers:
        print("[WARN] No se encontró ninguna capa convolucional conectada al forward-pass.")
        return

    feature_extractor = create_feature_extractor(model_map[int(id_disease)]["model"], connected_conv_layers)
    device = ""
    if tf.config.list_physical_devices('GPU'):
        print("✅ Se usará GPU")
        device = "GPU"
    else:
        print("⚠️ No hay GPU disponible, se usará CPU")
        device = "CPU"
    feature_maps_list = feature_extractor.predict(img)

    # 🔧 Feature maps que deseas guardar
    allowed_maps = [layer["name"] for layer in model_map[int(id_disease)]["layers"]]
    data_sql = []
    for layer, feature_maps in zip(connected_conv_layers, feature_maps_list):
        n_features = feature_maps.shape[-1]
        for i in range(n_features):
            filename = f"{layer.name}_fm_{i+1}.jpg"
            if filename not in allowed_maps:
                continue

            fm = feature_maps[0, :, :, i]
            
            plt.figure(figsize=(4, 4))
            plt.imshow(fm, cmap='viridis')
       
            plt.axis('off')

            save_path = os.path.join(output_dir, filename)
            save_path_replace = save_path.replace("../hanei/backend/", "")
            data_sql.append({
                "path":save_path_replace,
                "feature_map":n_features,
                "layer_name":f"{layer.name}_fm_{i+1}",
            })
            plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
            plt.close()
    inference_time = round((time.time() - start_time) * 1000, 2)
    return {
        "time_inference": inference_time,
        "device":device,
        "id_model":model_map[int(id_disease)]["id_model"],
         "layers": data_sql,

    }


def __main__():
    global model_map
    model_map = init_fm_models_from_sql()
__main__()
"""
def main():
    img_path = r"f:\dataset\fundus\images\aptos\train_images_crop\0369f3efe69b.png"
    output_dir = r"f:\dataset\fundus\images\aptos\featuremaps"
    visualize_feature_maps( img_path, output_dir)

if __name__ == "__main__":
    main()

"""