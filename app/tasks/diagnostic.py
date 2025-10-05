from PIL import Image
import torch
import torch.nn.functional as F
import time
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

from .stages_ViT import predict_image as predict_image_stages
from .biomarkers_vit import predict_image as predict_image_biomarkers

# Variables globales del modelo LLM
tok = None
model = None

# ────────────────────────────────
def ini_llm_model():
    global model, tok  # Importante para usar y modificar variables globales

    base_model_id = "NousResearch/Llama-2-7b-hf"
    lora_checkpoint = r"F:\codigo\uabc_llm\models\models\diagnostic_nlp"
    print("📦 Cargando modelo LLaMA con LoRA...")
    tok = AutoTokenizer.from_pretrained(base_model_id, use_fast=False)
    tok.pad_token = tok.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model = PeftModel.from_pretrained(base, lora_checkpoint)
    model.eval()
    print("✅ Modelo cargado correctamente.")
# ────────────────────────────────

def build_prompt(data_stages, data_biomarkers):
    stage_text = data_stages["predicted_label"]
    if data_biomarkers["predicted_labels"]:
        biomarker_names = [
            data_biomarkers["biomarkers"][str(i)] for i in data_biomarkers["predicted_labels"]
        ]
        biomarkers_text = ", ".join(biomarker_names)
    else:
        biomarkers_text = "none"
    return f"biomarkers: {biomarkers_text} | diagnosis: {stage_text}"

def generate_diagnostic(prompt, max_new_tokens=120):
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            top_k=50,
            temperature=0.8,
            pad_token_id=tok.pad_token_id
        )
    decoded = tok.decode(output[0], skip_special_tokens=True)
    return decoded[len(prompt):].strip()

def predict_image(image_path):
    start_time = time.time()

    # 1. Detectar biomarcadores primero
    data_biomarkers = predict_image_biomarkers(image_path)

    if data_biomarkers["predicted_labels"]:  # Si hay al menos 1 biomarcador
        prompt = build_prompt({"predicted_label": "abnormal"}, data_biomarkers)
        data_stages = {}  # para retorno coherente
    else:
        # No hay biomarcadores → usar modelo de etapas
        data_stages = predict_image_stages(image_path)
        if data_stages["predicted_label"] == "normal":
            prompt = "biomarkers: none | diagnosis: normal fundus"
        else:
            prompt = build_prompt(data_stages, data_biomarkers)

    print("🧾 Prompt generado:", prompt)
    diagnostic_text = generate_diagnostic(prompt)
    inference_time = round((time.time() - start_time) * 1000, 2)

    return {
        "prompt": prompt,
        "diagnostic": diagnostic_text,
        "labels_stage": data_stages.get("labels", {}),
        "labels_biomarkers": data_biomarkers["biomarkers"],
        "summary_stage": data_stages.get("summary", []),
        "summary_biomarkers": data_biomarkers["summary"],
        "time_inference": inference_time
    }

# Llamar una sola vez para inicializar el modelo LLM
ini_llm_model()
