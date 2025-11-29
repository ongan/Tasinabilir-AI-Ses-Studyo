import os
import sys
import time
import json
import gc
import shutil
import datetime

# --- YAMALAR ---
try:
    import transformers
    from transformers.generation.beam_search import BeamSearchScorer
    transformers.BeamSearchScorer = BeamSearchScorer
    import huggingface_hub
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download
except: pass

import torch
from TTS.api import TTS
from pydub import AudioSegment
from diffusers import StableDiffusionXLPipeline, StableVideoDiffusionPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from diffusers.utils import load_image, export_to_video
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from transformers import CLIPVisionModelWithProjection
from deep_translator import GoogleTranslator
from PIL import Image # Kukla resim için

# --- AYARLAR ---
print("\n==================================================")
print(">>> MULTİMEDYA FABRİKASI (V14.5 - FIXED) <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")
ref_folder = os.path.join(base_path, "References")
lora_folder = os.path.join(base_path, "Lora")

for f in [input_folder, output_folder, voices_folder, ambience_folder, ref_folder, lora_folder]:
    os.makedirs(f, exist_ok=True)

tools_path = os.path.dirname(base_path)
ffmpeg_bin = os.path.join(tools_path, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
AudioSegment.converter = ffmpeg_bin

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- GLOBAL MODEL ---
tts = None
pipe_image = None
pipe_video = None

# --- MOTOR YÖNETİMİ ---
def bellek_temizle():
    if device == "cuda": torch.cuda.empty_cache(); gc.collect()

def ses_motoru_yukle():
    global tts
    if tts is None:
        print("   🔊 Ses Motoru Yükleniyor...")
        bellek_temizle()
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

def video_motoru_yukle():
    global pipe_video, pipe_image
    if pipe_image is not None:
        del pipe_image; pipe_image = None; bellek_temizle()

    if pipe_video is None:
        print("   🎥 Video Motoru Yükleniyor...")
        try:
            pipe_video = StableVideoDiffusionPipeline.from_pretrained("stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16").to(device)
            pipe_video.enable_model_cpu_offload()
        except Exception as e: print(f"❌ Video Motoru Hatası: {e}")

def resim_motoru_yukle():
    global pipe_image, pipe_video
    if pipe_video is not None:
        del pipe_video; pipe_video = None; bellek_temizle()

    if pipe_image is None:
        print("   🎨 Resim Motoru (SDXL Base) Yükleniyor...")
        try:
            image_encoder = CLIPVisionModelWithProjection.from_pretrained("h94/IP-Adapter", subfolder="models/image_encoder", torch_dtype=torch.float16).to(device)
            base = "stabilityai/stable-diffusion-xl-base-1.0"
            repo = "ByteDance/SDXL-Lightning"
            ckpt = "sdxl_lightning_4step_unet.safetensors"
            ckpt_path = hf_hub_download(repo, ckpt)
            unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(device, torch.float16)
            unet.load_state_dict(load_file(ckpt_path, device=device))
            
            pipe_image = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, image_encoder=image_encoder, torch_dtype=torch.float16, variant="fp16").to(device)
            pipe_image.scheduler = EulerDiscreteScheduler.from_config(pipe_image.scheduler.config, timestep_spacing="trailing")
            pipe_image.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter-plus_sdxl_vit-h.safetensors")
            pipe_image.enable_model_cpu_offload()
        except Exception as e: print(f"❌ Resim Motoru Hatası: {e}")

# --- YARDIMCI ---
def metni_temizle(ham_metin):
    temiz = ham_metin.replace("—", ", ").replace("…", ".").replace("\n", " ")
    return " ".join(temiz.split())

def ceviri_yap(metin, hedef_dil):
    if hedef_dil == "tr" or hedef_dil == "auto": return metin
    try:
        cevirmen = GoogleTranslator(source='auto', target=hedef_dil)
        sonuc = cevirmen.translate(metin)
        # Log kirliliği yapmasın diye print'i kıstık
        return sonuc
    except: return metin

def srt_format(saniye):
    td = datetime.timedelta(seconds=saniye)
    zaman = str(td)
    if "." in zaman: ana, mili = zaman.split("."); mili = mili[:3]
    else: ana = zaman; mili = "000"
    if len(ana.split(":")[0]) == 1: ana = "0" + ana
    return f"{ana},{mili}"

def sahne_uret(prompt, kanal_ayarlari, kayit_yolu_img, kayit_yolu_vid, video_istegi, ref_resimler=None):
    resim_motoru_yukle()
    if pipe_image is None: return False
    try:
        final_prompt = f"{kanal_ayarlari['prompt_prefix']}, {prompt}, {kanal_ayarlari['prompt_suffix']}"
        print(f"   🎨 Çiziliyor: {prompt[:20]}... (Mod: {kanal_ayarlari['name']})")
        
        args = {
            "prompt": final_prompt,
            "num_inference_steps": 4, 
            "guidance_scale": 0, 
            "negative_prompt": kanal_ayarlari['negative_prompt']
        }

        # --- FIX: KUKLA RESİM MANTIĞI ---
        # IP-Adapter yüklü olduğu için model HER ZAMAN bir resim inputu ister.
        # Eğer referans yoksa, boş siyah bir resim (Dummy) veriyoruz.
        
        girecek_resimler = []
        if ref_resimler and len(ref_resimler) > 0:
            for r in ref_resimler:
                p = os.path.join(ref_folder, r.strip())
                if os.path.exists(p): girecek_resimler.append(load_image(p))
            
            if girecek_resimler:
                # Gerçek referans var -> Etkiyi aç
                scale = 0.4 if kanal_ayarlari['name'] == "Finans" else 0.65
                pipe_image.set_ip_adapter_scale(scale)
        
        if not girecek_resimler:
            # Referans yok -> Kukla resim ver ve etkiyi SIFIRLA
            dummy_image = Image.new("RGB", (224, 224), (0, 0, 0))
            girecek_resimler = [dummy_image]
            pipe_image.set_ip_adapter_scale(0.0) # Etki sıfır, yani dikkate alma

        # Resimleri argümana ekle (Hatayı önler)
        args["ip_adapter_image"] = girecek_resimler

        image = pipe_image(**args).images[0]
        image = image.resize((1024, 576))
        image.save(kayit_yolu_img)
        
        if video_istegi and kanal_ayarlari['video_allowed']:
            print("   🎥 Video Render...")
            video_motoru_yukle()
            frames = pipe_video(image, decode_chunk_size=2, generator=torch.manual_seed(42), motion_bucket_id=127).frames[0]
            export_to_video(frames, kayit_yolu_vid, fps=7)
            resim_motoru_yukle()
            
        return True
    except Exception as e: print(f"   ⚠️ Hata: {e}"); return False

# --- KANAL KATALOĞU ---
def get_kanal_ayarlari(kanal_adi):
    kanal_adi = str(kanal_adi).lower().strip()
    if "finans" in kanal_adi:
        return {
            "name": "Finans",
            "prompt_prefix": "minimalist stick figure drawing, hand drawn doodle, black ink on white paper, funny sketch",
            "prompt_suffix": "simple lines, cartoon style, whitespace",
            "negative_prompt": "realistic, photo, shading, complex, color, 3d render, blurry, detailed face",
            "video_allowed": False
        }
    elif "uyku" in kanal_adi or "meditasyon" in kanal_adi:
        return {
            "name": "Uyku",
            "prompt_prefix": "cinematic shot, peaceful atmosphere, soft lighting, dreamy, 8k, photorealistic",
            "prompt_suffix": "highly detailed, masterpiece, nature",
            "negative_prompt": "ugly, blurry, text, distortion, scary, dark",
            "video_allowed": True
        }
    elif "tarih" in kanal_adi:
        return {
            "name": "Tarih",
            "prompt_prefix": "historical oil painting style, epic cinematic shot, dramatic lighting",
            "prompt_suffix": "intricate details, museum quality",
            "negative_prompt": "modern, anime, cartoon, text, blur",
            "video_allowed": True
        }
    else:
        return {
            "name": "Genel",
            "prompt_prefix": "cinematic scene, high quality",
            "prompt_suffix": "4k, detailed",
            "negative_prompt": "blurry, ugly",
            "video_allowed": True
        }

# --- ANA DÖNGÜ ---
print("✅ SİSTEM HAZIR! İŞ BEKLENİYOR...")
ses_motoru_yukle()

while True:
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    if not files: time.sleep(1); continue

    json_file = files[0]
    json_path = os.path.join(input_folder, json_file)
    print(f"\n🎬 İŞ ALINDI: {json_file}")
    time.sleep(0.5)

    try:
        with open(json_path, "r", encoding="utf-8") as f: data = json.load(f)
        
        ham_icerik = data["metin"]
        ses_adi = data.get("ses", "Ses Yok")
        fon_adi = data.get("fon", "Yok")
        
        # --- PARSING DÜZELTMESİ ---
        # Satır satır, boşlukları temizleyerek oku
        lines = [l.strip() for l in ham_icerik.splitlines() if l.strip()]
        
        hedef_dil = "tr"
        kanal_tipi = "Genel"
        
        # Etiketleri ara (Büyük/Küçük harf duyarsız)
        for l in lines[:15]: # İlk 15 satıra bak
            l_upper = l.upper()
            if l_upper.startswith("DIL:") or l_upper.startswith("LANG:"):
                hedef_dil = l.split(":")[1].strip().lower()
            if l_upper.startswith("KANAL:") or l_upper.startswith("CHANNEL:"):
                kanal_tipi = l.split(":")[1].strip()

        kanal_config = get_kanal_ayarlari(kanal_tipi)
        print(f"📺 Kanal: {kanal_config['name']} | 🌍 Dil: {hedef_dil}")

        if not ses_adi.endswith(('.wav', '.mp3')): ses_adi += ".wav"
        ref_path = os.path.join(voices_folder, ses_adi)
        if not os.path.exists(ref_path):
            print(f"❌ SES YOK: {ses_adi}"); os.remove(json_path); continue

        proje_adi = json_file.replace(".json", "")
        proje_klasoru = os.path.join(output_folder, proje_adi)
        os.makedirs(proje_klasoru, exist_ok=True)

        satirlar = lines # Temizlenmiş satırları kullan
        aktif_prompt = "scene"
        aktif_referanslar = []
        video_modu = False
        
        sayac = 1
        full_audio_mix = AudioSegment.empty()
        srt_icerigi = ""
        srt_sayac = 1
        gecen_ms = 0

        for satir in satirlar:
            if any(satir.upper().startswith(x) for x in ["[REF:", "[IMG:", "[VID:", "DIL:", "KANAL:", "SES:", "FON:"]):
                if satir.upper().startswith("[REF:"): 
                    aktif_referanslar = [r.strip() for r in satir.split(":")[1].strip(" ]").split(",")]
                elif satir.upper().startswith("[IMG:"): 
                    aktif_prompt = satir.split(":")[1].strip(" ]"); video_modu = False
                elif satir.upper().startswith("[VID:"): 
                    aktif_prompt = satir.split(":")[1].strip(" ]"); video_modu = True
                continue

            img_out = os.path.join(proje_klasoru, f"{sayac:03d}_image.png")
            vid_out = os.path.join(proje_klasoru, f"{sayac:03d}_video.mp4")
            
            gercek_video = video_modu and kanal_config['video_allowed']
            sahne_uret(aktif_prompt, kanal_config, img_out, vid_out, gercek_video, aktif_referanslar)

            temiz = metni_temizle(satir)
            if len(temiz) < 2: continue
            
            okunacak = ceviri_yap(temiz, hedef_dil)
            print(f"   🗣️  Okunuyor ({hedef_dil}): {okunacak[:30]}...")
            
            temp_wav = "temp_line.wav"
            bellek_temizle()
            tts.tts_to_file(text=okunacak, speaker_wav=ref_path, language=hedef_dil, file_path=temp_wav, split_sentences=False, speed=1.0, temperature=0.65, repetition_penalty=2.0)
            
            parca = AudioSegment.from_wav(temp_wav)
            parca.export(os.path.join(proje_klasoru, f"{sayac:03d}_audio.wav"), format="wav")
            
            dur = len(parca)
            srt_icerigi += f"{srt_sayac}\n{srt_format(gecen_ms/1000)} --> {srt_format((gecen_ms+dur)/1000)}\n{okunacak}\n\n"
            srt_sayac += 1
            
            full_audio_mix += parca + AudioSegment.silent(duration=300)
            gecen_ms += dur + 300
            sayac += 1

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
        with open(os.path.join(proje_klasoru, "ALTYAZI.srt"), "w", encoding="utf-8") as f: f.write(srt_icerigi)
        print(f"✅ BİTTİ: {proje_adi}")
        os.remove(json_path)
        if os.path.exists("temp_line.wav"): os.remove("temp_line.wav")

    except Exception as e:
        print(f"❌ HATA: {e}"); 
        if os.path.exists(json_path): os.remove(json_path)