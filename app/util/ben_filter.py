import numpy as np
import cv2
import os
import warnings
warnings.filterwarnings("ignore")

def load_ben_color(path, sigmaX=10):
    image = cv2.imread(path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.addWeighted(image, 4, cv2.GaussianBlur(image, (0, 0), sigmaX), -4, 128)
    return image

def process_ben_image(image_path,baseImagePath, suffix=''):
    # Procesar la imagen
    output_path = baseImagePath + "/original_ben_filter.jpg"
    processed_image = load_ben_color(image_path, sigmaX=30)
    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)

    # Preparar nombre de archivo de salida
    base_name = os.path.basename(image_path)
    base, _ = os.path.splitext(base_name)
    output_filename = f"{base}{suffix}.jpg"

    # Guardar la imagen procesada
    #full_output_path = os.path.join(output_path, output_filename)
    cv2.imwrite(output_path, cv2.cvtColor(processed_image, cv2.COLOR_RGB2BGR))
    return output_path