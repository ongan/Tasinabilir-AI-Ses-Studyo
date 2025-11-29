import torch
from TTS.api import TTS
import os
import time

print("--- 1. BAŞLANGIÇ ---")

# CUDA Kontrolü
if torch.cuda.is_available():
    print("✅ CUDA (Ekran Kartı) görüldü!")
    device = "cuda"
else:
    print("❌ DİKKAT: Ekran kartı görülmedi, CPU kullanılacak.")
    device = "cpu"

print(f"--- 2. MODEL YÜKLENİYOR ({device}) ---")
try:
    # gpu=True parametresini sildim, standart yükleme yapıyoruz.
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print("✅ Model Başarıyla Yüklendi!")
except Exception as e:
    print(f"❌ MODEL YÜKLEME HATASI: {e}")
    exit()

print("--- 3. SES ÜRETİMİ BAŞLIYOR ---")
text = "Merhaba, bu bir sistem kontrol testidir."
output_path = "test_cikti.wav"

try:
    start_time = time.time()
    
    # En basit haliyle üretim deniyoruz
    tts.tts_to_file(
        text=text,
        speaker_wav="referans.wav", # Klasöründe 'referans.wav' olduğundan emin ol!
        language="tr",
        file_path=output_path
    )
    
    end_time = time.time()
    print(f"✅ İŞLEM BAŞARILI! Süre: {end_time - start_time:.2f} saniye")
    print(f"Dosya konumu: {os.path.abspath(output_path)}")

except Exception as e:
    print(f"❌ ÜRETİM SIRASINDA HATA: {e}")

print("--- TEST BİTTİ ---")