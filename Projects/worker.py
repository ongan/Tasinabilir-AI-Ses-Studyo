import os
import sys
import time
import json
import gc
import shutil

# --- SUPER PATCH ---
print("\n🔧 SİSTEM YAMANIYOR...")
try:
    import transformers
    from transformers.generation.beam_search import BeamSearchScorer
    transformers.BeamSearchScorer = BeamSearchScorer
    
    import huggingface_hub
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download
    print("✅ YAMALAR BAŞARILI.")
except: pass

import torch
from TTS.api import TTS
from pydub import AudioSegment
from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from diffusers.utils import load_image
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
# YENİ EKLENEN PARÇA: Görüntü Kodlayıcı
from transformers import CLIPVisionModelWithProjection

# --- AYARLAR ---
print("\n==================================================")
print(">>> MULTİMEDYA FABRİKASI (V9.5 - IP-ADAPTER FIX) <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")
ref_folder = os.path.join(base_path, "References")

for f in [input_folder, output_folder, voices_folder, ambience_folder, ref_folder]:
    os.makedirs(f, exist_ok=True)

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
    
    # 2. Görüntü Kodlayıcı (Image Encoder) - BU KISIM EKSİKTİ, EKLENDİ
    print("   -> Görüntü Kodlayıcı (CLIP Vision) Yükleniyor...")
    image_encoder = CLIPVisionModelWithProjection.from_pretrained(
        "h94/IP-Adapter", 
        subfolder="models/image_encoder", 
        torch_dtype=torch.float16
    ).to(device)

    # 3. Görsel Model (SDXL)
    print("   -> SDXL Lightning Yükleniyor...")
    base = "stabilityai/stable-diffusion-xl-base-1.0"
    repo = "ByteDance/SDXL-Lightning"
    ckpt = "sdxl_lightning_4step_unet.safetensors"
    
    ckpt_path = hf_hub_download(repo, ckpt)
    unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(device, torch.float16)
    unet.load_state_dict(load_file(ckpt_path, device=device))
    
    # Pipeline'a image_encoder'ı tanıtıyoruz
    pipe = StableDiffusionXLPipeline.from_pretrained(
        base, 
        unet=unet, 
        image_encoder=image_encoder, # <--- KRİTİK DÜZELTME BURADA
        torch_dtype=torch.float16, 
        variant="fp16"
    ).to(device)
    
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    
    # 4. IP-Adapter (TUTARLILIK MODÜLÜ)
    print("   -> IP-Adapter Aktif Ediliyor...")
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter-plus_sdxl_vit-h.safetensors")
    
    # VRAM Tasarrufu
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

def gorsel_uret(prompt, kayit_yolu, ref_resimler=None):
    if pipe is None: return False
    try:
        print(f"   🎨 Resim: {prompt[:30]}...")
        
        args = {
            "prompt": prompt,
            "num_inference_steps": 4, 
            "guidance_scale": 0,
            "negative_prompt": "blurry, low quality, ugly, deformed, text, watermark"
        }

        if ref_resimler and len(ref_resimler) > 0:
            print(f"      🔗 Tutarlılık Modu: {len(ref_resimler)} referans")
            loaded_refs = []
            for r in ref_resimler:
                p = os.path.join(ref_folder, r.strip())
                if os.path.exists(p):
                    # Resmi yükle ve boyutunu kontrol et
                    img = load_image(p)
                    loaded_refs.append(img)
                else:
                    print(f"      ⚠️ Referans bulunamadı: {r}")
            
            if loaded_refs:
                args["ip_adapter_image"] = loaded_refs
                pipe.set_ip_adapter_scale(0.65)
        else:
            pipe.set_ip_adapter_scale(0.0)

        image = pipe(**args).images[0]
        image.save(kayit_yolu)
        return True
    except Exception as e:
        print(f"   ⚠️ Resim Hatası: {e}")
        # Hata olsa bile sistemi durdurma, devam et
        return False

# --- ANA DÖNGÜ ---
while True:
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    if not files:
        time.sleep(1)
        continue

    json_file = files[0]
    json_path = os.path.join(input_folder, json_file)
    print(f"\n🎬 İŞ ALINDI: {json_file}")
    time.sleep(0.5)

    try:
        with open(json_path, "r", encoding="utf-8") as f: data = json.load(f)

        ham_icerik = data["metin"]
        ses_adi = data.get("ses", "Ses Yok")
        fon_adi = data.get("fon", "Yok")

        if not ses_adi.endswith(('.wav', '.mp3')): ses_adi += ".wav"
        ref_path = os.path.join(voices_folder, ses_adi)
        if not os.path.exists(ref_path):
            print(f"❌ SES YOK: {ses_adi}"); os.remove(json_path); continue

        proje_adi = json_file.replace(".json", "")
        proje_klasoru = os.path.join(output_folder, proje_adi)
        os.makedirs(proje_klasoru, exist_ok=True)

        satirlar = ham_icerik.split("\n")
        aktif_prompt = "Cinematic scene, high quality, 8k"
        aktif_referanslar = []
        
        sayac = 1
        full_audio_mix = AudioSegment.empty()

        for satir in satirlar:
            satir = satir.strip()
            if not satir: continue

            if satir.startswith("[REF:") or satir.startswith("[REFERANS:"):
                refs_raw = satir.split(":", 1)[1].strip(" ]")
                aktif_referanslar = [r.strip() for r in refs_raw.split(",")]
                print(f"   🔗 Referans Kilitlendi: {aktif_referanslar}")
                continue
            
            if satir.startswith("[IMG:") or satir.startswith("[GÖRSEL:"):
                aktif_prompt = satir.split(":", 1)[1].strip(" ]")
                continue

            # A) Resim
            gorsel_uret(aktif_prompt, os.path.join(proje_klasoru, f"{sayac:03d}_sahne.png"), aktif_referanslar)

            # B) Ses
            temiz_cumle = metni_temizle(satir)
            if len(temiz_cumle) < 2: continue

            print(f"   🗣️ Okunuyor: {temiz_cumle[:30]}...")
            temp_wav = "temp_line.wav"
            if device == "cuda": torch.cuda.empty_cache(); gc.collect()

            tts.tts_to_file(text=temiz_cumle, speaker_wav=ref_path, language="tr", file_path=temp_wav, split_sentences=False, speed=1.0, temperature=0.65, repetition_penalty=2.0)

            parca = AudioSegment.from_wav(temp_wav)
            parca.export(os.path.join(proje_klasoru, f"{sayac:03d}_ses.wav"), format="wav")
            full_audio_mix += parca + AudioSegment.silent(duration=300)
            sayac += 1

        # C) Fon
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

        full_audio_mix.export(os.path.join(proje_klasoru, "FINAL.wav"), format="wav")
        print(f"✅ BİTTİ: {proje_adi}")
        os.remove(json_path)
        if os.path.exists("temp_line.wav"): os.remove("temp_line.wav")

    except Exception as e:
        print(f"❌ İŞLEM HATASI: {e}"); 
        if os.path.exists(json_path): os.remove(json_path)