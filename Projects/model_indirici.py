import os
import torch
from huggingface_hub import hf_hub_download
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from safetensors.torch import load_file # <--- SİHİRLİ PARÇA BU

print("\n==================================================")
print("     GÖRSEL MODELİ İNDİRİCİSİ (FIXED)")
print("==================================================\n")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Hedef Donanım: {device.upper()}")

try:
    # 1. Önce Temel SDXL Modelini İndiriyoruz
    print("\n>>> 1/2: Temel SDXL Modeli İndiriliyor (Base)...")
    base_model = "stabilityai/stable-diffusion-xl-base-1.0"
    
    pipe = StableDiffusionXLPipeline.from_pretrained(
        base_model, 
        torch_dtype=torch.float16, 
        variant="fp16", 
        use_safetensors=True
    )
    print("✅ Temel Model Hazır!\n")

    # 2. Şimdi Lightning (Hızlandırıcı) Dosyasını İndiriyoruz
    print(">>> 2/2: Lightning Hızlandırıcısı İndiriliyor...")
    repo = "ByteDance/SDXL-Lightning"
    checkpoint = "sdxl_lightning_4step_unet.safetensors"
    
    # Dosyayı indir
    downloaded_path = hf_hub_download(repo_id=repo, filename=checkpoint)
    print(f"✅ Dosya İndi: {checkpoint}\n")

    print("--- DOĞRULAMA TESTİ YAPILIYOR ---")
    
    # UNet iskeletini oluştur
    unet = UNet2DConditionModel.from_config(base_model, subfolder="unet").to(device, torch.float16)
    
    # DÜZELTİLEN KISIM BURASI: torch.load YERİNE load_file KULLANIYORUZ
    unet.load_state_dict(load_file(downloaded_path, device=device))
    
    pipe.unet = unet
    pipe.to(device)
    
    print("🎉 MÜKEMMEL! Sistem başarıyla kuruldu.")
    
except Exception as e:
    print(f"\n❌ HATA: {e}")
    import traceback
    traceback.print_exc()

input("\nÇıkmak için Enter'a bas...")