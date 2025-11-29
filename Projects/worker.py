import os
import sys

# ==========================================
# >>> SUPER PATCH (ÇİFTE YAMA) BAŞLANGICI <<<
# ==========================================
print("\n🔧 SİSTEM YAMANIYOR (Uyumluluk Modu)...")
try:
    # 1. YAMA: Transformers (Ses Motoru İçin)
    import transformers
    from transformers.generation.beam_search import BeamSearchScorer
    transformers.BeamSearchScorer = BeamSearchScorer
    
    # 2. YAMA: Huggingface Hub (Görüntü Motoru İçin)
    import huggingface_hub
    # Eski 'cached_download' komutunu yeni 'hf_hub_download'a yönlendiriyoruz
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download
    
    print("✅ YAMALAR BAŞARILI: Sistem uyumlu hale getirildi.")
except Exception as e:
    print(f"⚠️ Yama Uyarısı: {e}")
# ==========================================
# >>> SUPER PATCH BİTİŞİ <<<
# ==========================================

import time
import json
import gc
import shutil
import torch
from TTS.api import TTS
from pydub import AudioSegment
# Yamadan SONRA import ediyoruz ki hata vermesin
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

# --- AYARLAR ---
print("\n==================================================")
print(">>> MULTİMEDYA FABRİKASI (V8.1 - STABLE) <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")

# FFmpeg
tools_path = os.path.dirname(base_path)
ffmpeg_bin = os.path.join(tools_path, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
AudioSegment.converter = ffmpeg_bin

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- MODEL YÜKLEME ---
print("--- Modeller Yükleniyor... ---")
try:
    # 1. Ses
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    
    # 2. Görsel
    base = "stabilityai/stable-diffusion-xl-base-1.0"
    repo = "ByteDance/SDXL-Lightning"
    ckpt = "sdxl_lightning_4step_unet.safetensors"
    
    ckpt_path = hf_hub_download(repo, ckpt)
    unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(device, torch.float16)
    unet.load_state_dict(load_file(ckpt_path, device=device))
    
    pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=torch.float16, variant="fp16").to(device)
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    pipe.enable_model_cpu_offload()

    print("✅ TÜM SİSTEM HAZIR! İŞ BEKLENİYOR...")

except Exception as e:
    print(f"❌ BAŞLANGIÇ HATASI: {e}")
    time.sleep(10)
    exit()

# --- YARDIMCI FONKSİYONLAR ---
def metni_temizle(ham_metin):
    temiz = ham_metin.replace("—", ", ").replace("…", ".").replace("\n", " ")
    return " ".join(temiz.split())

def gorsel_uret(prompt, kayit_yolu):
    if pipe is None: return False
    try:
        print(f"   🎨 Resim: {prompt[:30]}...")
        image = pipe(prompt=prompt, num_inference_steps=4, guidance_scale=0).images[0]
        image.save(kayit_yolu)
        return True
    except Exception as e:
        print(f"   ⚠️ Resim Hatası: {e}")
        return False

# --- ANA DÖNGÜ ---
while True:
    # 1. Bekleme Modu
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    if not files:
        time.sleep(1)
        continue

    # 2. İş Yakalama
    json_file = files[0]
    json_path = os.path.join(input_folder, json_file)
    print(f"\n🎬 İŞ ALINDI: {json_file}")
    time.sleep(0.5)

    try:
        # 3. Veri Okuma
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ham_icerik = data["metin"]
        ses_adi = data.get("ses", "Ses Yok")
        fon_adi = data.get("fon", "Yok")

        if not ses_adi.endswith(('.wav', '.mp3')): ses_adi += ".wav"
        ref_path = os.path.join(voices_folder, ses_adi)
        
        if not os.path.exists(ref_path):
            print(f"❌ SES YOK: {ses_adi}")
            os.remove(json_path)
            continue

        # 4. Hazırlık
        proje_adi = json_file.replace(".json", "")
        proje_klasoru = os.path.join(output_folder, proje_adi)
        os.makedirs(proje_klasoru, exist_ok=True)
        print(f"📂 Kayıt: {proje_klasoru}")

        satirlar = ham_icerik.split("\n")
        aktif_prompt = "Cinematic scene, high quality, 8k"
        sayac = 1
        full_audio_mix = AudioSegment.empty()

        # 5. Satır Satır İşleme
        for satir in satirlar:
            satir = satir.strip()
            if not satir: continue

            # Görsel Komutu mu?
            if satir.startswith("[IMG:") or satir.startswith("[GÖRSEL:"):
                aktif_prompt = satir.split(":", 1)[1].strip(" ]")
                print(f"   📌 Sahne: {aktif_prompt}")
                continue

            # A) Resim Çiz
            gorsel_uret(aktif_prompt, os.path.join(proje_klasoru, f"{sayac:03d}_sahne.png"))

            # B) Ses Üret
            temiz_cumle = metni_temizle(satir)
            if len(temiz_cumle) < 2: continue

            print(f"   🗣️ Okunuyor: {temiz_cumle[:30]}...")
            temp_wav = "temp_line.wav"
            
            if device == "cuda": torch.cuda.empty_cache(); gc.collect()

            tts.tts_to_file(
                text=temiz_cumle, speaker_wav=ref_path, language="tr", file_path=temp_wav,
                split_sentences=False, speed=1.0, temperature=0.65, repetition_penalty=2.0
            )

            parca = AudioSegment.from_wav(temp_wav)
            parca.export(os.path.join(proje_klasoru, f"{sayac:03d}_ses.wav"), format="wav")
            full_audio_mix += parca + AudioSegment.silent(duration=300)
            sayac += 1

        # 6. Fon Müziği
        if fon_adi and fon_adi != "Yok":
            print(f"🎹 Fon: {fon_adi}")
            fon_yolu = None
            for ext in [".mp3", ".wav"]:
                pot = os.path.join(ambience_folder, fon_adi + ext)
                if os.path.exists(pot): fon_yolu = pot; break
            
            if fon_yolu:
                fon = AudioSegment.from_file(fon_yolu) - 18
                while len(fon) < len(full_audio_mix) + 2000: fon += fon
                fon = fon[:len(full_audio_mix) + 1000].fade_out(2000)
                full_audio_mix = fon.overlay(full_audio_mix)

        # 7. Kaydet ve Temizle
        full_audio_mix.export(os.path.join(proje_klasoru, "FINAL.wav"), format="wav")
        print(f"✅ BİTTİ: {proje_adi}")
        
        os.remove(json_path)
        if os.path.exists("temp_line.wav"): os.remove("temp_line.wav")

    except Exception as e:
        print(f"❌ İŞLEM HATASI: {e}")
        if os.path.exists(json_path): os.remove(json_path)