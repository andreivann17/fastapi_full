import platform
import socket
import psutil
import GPUtil
import os
import subprocess

def get_cpu_vendor():
    cpu_info = platform.processor().lower()
    if "intel" in cpu_info:
        return "Intel"
    elif "amd" in cpu_info:
        return "AMD"
    elif "arm" in cpu_info:
        return "ARM"
    else:
        return "Unknown"

def get_system_uuid():
    if platform.system() == "Windows":
        return subprocess.check_output('wmic csproduct get uuid', shell=True).decode().split('\n')[1].strip()
    elif platform.system() == "Linux":
        return subprocess.check_output('cat /sys/class/dmi/id/product_uuid', shell=True).decode().strip()
    else:
        return "UUID not supported on this OS"

def get_gpu_vendor(model_name):
    model_lower = model_name.lower()
    if "nvidia" in model_lower:
        return "NVIDIA"
    elif "amd" in model_lower or "radeon" in model_lower:
        return "AMD"
    elif "intel" in model_lower:
        return "Intel"
    elif "apple" in model_lower or "m1" in model_lower:
        return "Apple"
    elif "npu" in model_lower:
        return "Integrated NPU"
    else:
        return "Unknown"

def get_hardware_info():
    cpu_model = platform.processor()
    cpu_vendor = get_cpu_vendor()
    cpu_ram_gb = round(psutil.virtual_memory().total / 1e9)
    cpu_cores = psutil.cpu_count(logical=False)
    computer_name = socket.gethostname()
    uuid = get_system_uuid()

    gpus = GPUtil.getGPUs()
    has_gpu = len(gpus) > 0
    content = []
    content.append( {"type": "CPU", "name": cpu_model, "vendor": cpu_vendor, "ram": cpu_ram_gb})

    if has_gpu:
        gpu = gpus[0]
        gpu_model = gpu.name
        gpu_vendor = get_gpu_vendor(gpu_model)
        gpu_ram_gb = round(gpu.memoryTotal)  # GPU RAM en GB
        content.append( {"type": "GPU", "name": gpu_model, "vendor": gpu_vendor, "ram": gpu_ram_gb})
   

    return {
        "uuid": uuid,
        "server_name": computer_name,
        "cpu_cores": cpu_cores,
        "content": content,
    }
