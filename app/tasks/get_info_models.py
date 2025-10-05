import tensorflow as tf
import torch
import onnx
import onnxruntime as ort
from fastapi import HTTPException
import os
from transformers import ViTForImageClassification, ViTImageProcessor


def analyze_keras_model(path):
    try:
        model = tf.keras.models.load_model(path)
        output_shape = model.output_shape
        # Soporte para múltiples salidas
        if isinstance(output_shape, list):
            num_classes = [shape[-1] for shape in output_shape]
        else:
            num_classes = output_shape[-1]
        return {
            "framework": "TensorFlow",
            "framework_key":"1",
            
            "num_layers": len(model.layers),
            "input_shape": model.input_shape,
            "output_shape": output_shape,
            "num_classes": num_classes,
            "summary": str([layer.name for layer in model.layers])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keras model error: {str(e)}")


def analyze_pytorch_model(path):
    try:
        model = torch.load(path, map_location='cpu')

        # Si es un modelo de torch.nn.Module
        if isinstance(model, torch.nn.Module):
            try:
                # Intenta inferir número de clases desde la última capa
                last_layer = list(model.children())[-1]
                if hasattr(last_layer, 'out_features'):
                    num_classes = last_layer.out_features
                else:
                    num_classes = "Unknown"
            except:
                num_classes = "Unknown"

            num_params = sum(p.numel() for p in model.parameters())
            return {
                "framework": "PyTorch",
                "framework_key":"2",
                "num_parameters": num_params,
                "has_state_dict": True,
                "num_classes": num_classes
            }

        # Si solo es un state_dict
        elif hasattr(model, 'state_dict') or isinstance(model, dict):
            return {
                "framework": "PyTorch",
                "framework_key":"2",
                "note": "The model is a raw object or state_dict. Cannot determine num_classes without architecture.",
                "num_classes": "Unknown"
            }

        else:
            return {
                "framework": "PyTorch",
                "note": "Unknown PyTorch model format.",
                "num_classes": "Unknown"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PyTorch model error: {str(e)}")


def analyze_onnx_model(path):
    try:
        model = onnx.load(path)
        onnx.checker.check_model(model)
        session = ort.InferenceSession(path)

        input_names = [inp.name for inp in session.get_inputs()]
        output_names = [out.name for out in session.get_outputs()]
        output_shapes = [out.shape for out in session.get_outputs()]
        # Asumir la última dimensión como número de clases si es conocido
        try:
            num_classes = output_shapes[0][-1]
        except:
            num_classes = "Unknown"

        return {
            "framework": "ONNX",
            "framework_key":"3",
            "inputs": input_names,
            "outputs": output_names,
            "ir_version": model.ir_version,
            "producer_name": model.producer_name,
            "num_classes": num_classes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ONNX model error: {str(e)}")


def analyze_vit_model(folder_path):
    try:
        model = ViTForImageClassification.from_pretrained(folder_path)
        processor = ViTImageProcessor.from_pretrained(folder_path)

        return {
            "framework": "HuggingFace",
            "framework_key":"4",
            "model_type": model.config.model_type,
            "num_labels": model.config.num_labels,
            "input_size": processor.size,
            "summary": model.config.to_dict(),
            "num_classes": model.config.num_labels
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ViT model error: {str(e)}")


def analyze_model(path, is_folder):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path does not exist.")

    if is_folder:
        if not os.path.exists(os.path.join(path, "model.safetensors")) or \
           not os.path.exists(os.path.join(path, "config.json")):
            raise HTTPException(status_code=400, detail="Missing model.safetensors or config.json")
        return analyze_vit_model(path)

    ext = os.path.splitext(path)[1].lower()

    if ext == '.h5':
        return analyze_keras_model(path)
    elif ext in ['.pt', '.pth']:
        return analyze_pytorch_model(path)
    elif ext == '.onnx':
        return analyze_onnx_model(path)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format.")
