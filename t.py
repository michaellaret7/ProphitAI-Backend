# my_script.py
import modal
import torch

process_pdf = modal.Function.from_name("test", "check_gpu")

# app = modal.App("test")

# @app.function(gpu="T4", image=modal.Image.debian_slim().pip_install("torch", "pytesseract"))
# def check_gpu() -> dict:
#     # Your OCR logic
#     tv = torch.__version__
#     dc = torch.cuda.device_count()
#     dn = torch.cuda.get_device_name()

#     return {"text": f"Torch v{tv}, Device count: {dc}, Device name: {dn}"}

x = process_pdf.remote()
print(x)