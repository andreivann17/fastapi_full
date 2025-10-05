import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
from tensorflow.keras.preprocessing.image import img_to_array, ImageDataGenerator
import cv2
import os

model_loaded = tf.keras.models.load_model("./models/features_maps/model_features_maps_myopia.h5")

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

def get_connected_conv_layers(model, target_layer_name, input_shape=(224,224,3)):
    connected_layers = []
    dummy_input = tf.zeros((1,) + input_shape)
    for layer in model.layers:
        if target_layer_name in layer.name:
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

def extract_high_activation_regions(img_path, output_dir, model, threshold=0.7):
    img = prepare_image(img_path)
    img_original = cv2.imread(img_path)
    img_original = cv2.cvtColor(img_original, cv2.COLOR_BGR2RGB)
    img_original = cv2.resize(img_original, (224, 224))

    os.makedirs(output_dir, exist_ok=True)
    
    connected_conv_layers = get_connected_conv_layers(model, "conv2d_376")

    if not connected_conv_layers:
        print("[WARN] No se encontró la capa 'conv2d_376' conectada al forward-pass.")
        return

    feature_extractor = create_feature_extractor(model, connected_conv_layers)
    feature_maps_list = feature_extractor.predict(img)

    # 🔧 Solución al error de dimensiones
    if not isinstance(feature_maps_list, list):
        feature_maps_list = [feature_maps_list]

    for layer, feature_maps in zip(connected_conv_layers, feature_maps_list):
        n_features = feature_maps.shape[-1]

        for i in range(n_features):
            fm = feature_maps[:, :, i]  # ✅ 3D tensor now
            if np.max(fm) < threshold:
                continue

            fm_resized = cv2.resize(fm, (224, 224))
            mask = fm_resized >= threshold
            segmented = np.zeros_like(img_original)
            segmented[mask] = img_original[mask]

            filename = f"{layer.name}_fm_{i+1}_segmented.png"
            save_path = os.path.join(output_dir, filename)
            plt.imsave(save_path, segmented)

    print("Segmentaciones generadas.")

def main():
    img_path = r"f:\codigo\UABCRetina\diabetic_macular_edema_web - copia\src\assets\img\gans\patchy\patchy.jpg"
    output_dir = r"f:\codigo\UABCRetina\diabetic_macular_edema_web - copia\src\assets\img\gans\patchymaps2"
    extract_high_activation_regions(img_path, output_dir, model_loaded)

if __name__ == "__main__":
    main()
