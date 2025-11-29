import os
from huggingface_hub import hf_hub_download

print("\n==================================================")
print(">>> STİL DOSYALARI (LoRA) İNDİRİCİSİ V2 <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
lora_folder = os.path.join(base_path, "Lora")
os.makedirs(lora_folder, exist_ok=True)

print(f"Hedef Klasör: {lora_folder}\n")

# --- LİSTE ---
modeller = [
    {
        "ad": "Çöp Adam (Stick Figure)",
        "repo": "Norod78/sdxl-stick-figure-lora-v1",
        "dosya": "StickFigure_v1_SDXL.safetensors"
    },
    {
        "ad": "Vektör Çizim (Flat Illustration)",
        "repo": "GoToCompany/sdxl-lora-vector-flat-illustration",
        "dosya": "sdxl_lora_vector_flat_illustration.safetensors"
    }
]

# --- İNDİRME DÖNGÜSÜ ---
for model in modeller:
    print(f"⬇️ İNDİRİLİYOR: {model['ad']}...")
    try:
        path = hf_hub_download(
            repo_id=model['repo'], 
            filename=model['dosya'], 
            local_dir=lora_folder
        )
        print(f"   ✅ BAŞARILI! Dosya şurada: {path}\n")
    except Exception as e:
        print(f"   ❌ HATA OLUŞTU!")
        print(f"   ⚠️ HATA DETAYI: {e}\n")

print("İşlem Bitti. Eğer hata gördüysen yukarıdaki mesajı oku.")
input("Çıkmak için Enter'a bas...")