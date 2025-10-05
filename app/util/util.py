import cv2
import numpy as np
from PIL import Image
import os

def extraer_pixeles_blancos_reales(path_save,input_path,output_path):

    imagen = cv2.imread(input_path)
    mascara = cv2.imread(output_path, cv2.IMREAD_GRAYSCALE)
    imagen_redimensionada = cv2.resize(imagen, (256, 256))
    mascara_redimensionada = cv2.resize(mascara, (256, 256))
    _, mascara_binaria = cv2.threshold(mascara_redimensionada, 127, 255, cv2.THRESH_BINARY)
    resultado_transparente = np.zeros((256, 256, 4), dtype=np.uint8)
    resultado_transparente[mascara_binaria == 255, :3] = imagen_redimensionada[mascara_binaria == 255] 
    resultado_transparente[mascara_binaria == 255, 3] = 255  

    cv2.imwrite(path_save, resultado_transparente)


def transparent_image(path_save, input_path):
    os.makedirs(os.path.dirname(path_save), exist_ok=True)

    mask = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    height, width = mask.shape

    transparent_img = np.zeros((height, width, 4), dtype=np.uint8)
    threshold = 180

    mask_foreground = mask >= threshold
    mask_background = ~mask_foreground

    # 🔵 Azul semi-transparente para el biomarcador detectado
    transparent_img[mask_foreground] = [0, 0, 255, 80]  # Azul (#0000FF50)

    # 🟢 Fondo totalmente transparente
    transparent_img[mask_background] = [0, 0, 0, 0]

    if not path_save.lower().endswith(".png"):
        path_save = path_save.rsplit(".", 1)[0] + ".png"

    Image.fromarray(transparent_img, mode="RGBA").save(path_save, format="PNG")

def crear_carpeta(base_path: str, nombre: str) -> str:
    """
    Crea una carpeta con el nombre dado dentro del path base.
    Retorna el path completo creado.
    """
    ruta_completa = os.path.join(base_path, nombre)

    if not os.path.exists(ruta_completa):
        os.makedirs(ruta_completa)
        print(f"📁 Carpeta creada: {ruta_completa}")
    else:
        print(f"✅ Carpeta ya existía: {ruta_completa}")

    return ruta_completa
