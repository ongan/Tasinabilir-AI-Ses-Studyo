import os
import sys
import time
import json
import gc
import shutil
import datetime
import re
import numpy as np
import cv2

# --- YAMALAR ---
try:
    import transformers
    from transformers.generation.beam_search import BeamSearchScorer
    transformers.BeamSearchScorer = BeamSearchScorer
    import huggingface_hub
    huggingface_hub.cached_download = huggingface_hub.hf_hub_download
except: pass

import torch
import ollama
from TTS.api import TTS
from pydub import AudioSegment, effects, silence
from diffusers import StableDiffusionXLPipeline, StableVideoDiffusionPipeline, AudioLDMPipeline, UNet2DConditionModel, EulerDiscreteScheduler
from diffusers.utils import load_image, export_to_video
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from transformers import CLIPVisionModelWithProjection
from deep_translator import GoogleTranslator
from PIL import Image
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.config import change_settings

# --- AYARLAR ---
print("\n==================================================")
print(">>> MULTİMEDYA FABRİKASI (V29.7 - FINAL SYNC FIX) <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")
ref_folder = os.path.join(base_path, "References")
lora_folder = os.path.join(base_path, "Lora")
sfx_folder = os.path.join(base_path, "SFX_Cache")

for f in [input_folder, output_folder, voices_folder, ambience_folder, ref_folder, lora_folder, sfx_folder]:
    os.makedirs(f, exist_ok=True)

tools_path = os.path.dirname(base_path)
ffmpeg_bin = os.path.join(tools_path, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
AudioSegment.converter = ffmpeg_bin
change_settings({"FFMPEG_BINARY": ffmpeg_bin})

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- GLOBAL ---
tts = None; pipe_image = None; pipe_video = None; pipe_audio = None

# --- YARDIMCI FONKSİYONLAR ---
def son_kareyi_yakala(video_path, save_path):
    """Videonun son karesini resim olarak kaydeder"""
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(save_path, frame)
                cap.release()
                return True
    except: pass
    return False

def get_kanal(kanal_adi):
    k = str(kanal_adi).lower().strip()
    if "finans" in k: return {"name": "Finans", "prompt": "minimalist stick figure...", "neg": "realistic, photo", "vid": False}
    if "uyku" in k: return {"name": "Uyku", "prompt": "cinematic shot, peaceful...", "neg": "ugly", "vid": True}
    if "korku" in k: return {"name": "Korku", "prompt": "horror scene, dark...", "neg": "happy", "vid": True}
    return {"name": "Genel", "prompt": "cinematic...", "neg": "blurry", "vid": True}

def clean_json(text):
    try: return json.loads(text)
    except: pass
    text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    start = text.find("{"); end = text.rfind("}")
    if start != -1: return json.loads(text[start:end+1], strict=False)
    return None

def srt_zamani(saniye):
    td = str(datetime.timedelta(seconds=saniye))
    if "." in td: ana, m = td.split("."); m = m[:3]
    else: ana = td; m = "000"
    if len(ana.split(":")[0])==1: ana="0"+ana
    return f"{ana},{m}"

def ceviri_yap(metin, hedef_dil):
    if hedef_dil == "auto" or hedef_dil == "tr": return metin
    try: return GoogleTranslator(source='auto', target=hedef_dil).translate(metin)
    except: return metin

def sesi_temizle(audio_seg):
    try:
        start_trim = silence.detect_leading_silence(audio_seg, silence_threshold=-40.0)
        end_trim = silence.detect_leading_silence(audio_seg.reverse(), silence_threshold=-40.0)
        return audio_seg[start_trim:len(audio_seg)-end_trim]
    except: return audio_seg

# --- SENARYO ÇÖZÜCÜLER ---
def ai_senaryo_analiz(ham_metin, dil="auto"):
    print("🧠 OLLAMA Düşünüyor...")
    prompt = f"""
    You are a Director. Output JSON only.
    INPUT: "{ham_metin}"
    LANG: "{dil}"
    JSON: {{ "channel": "Korku", "language": "en", "scenes": [ {{ "text": "...", "img_prompt": "...", "type": "image" }} ] }}
    """
    try:
        resp = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}], format='json')
        return clean_json(resp['message']['content'])
    except: return None

def manuel_senaryo_coz(ham_metin):
    print("📋 Manuel Mod Aktif.")
    satirlar = ham_metin.split('\n')
    scenes = []
    current_prompt = "cinematic scene"; current_type = "image"
    kanal = "Genel"; dil = "en"
    
    for line in satirlar:
        line = line.strip()
        if not line: continue
        
        if line.startswith("KANAL:"): kanal = line.split(":")[1].strip()
        elif line.startswith("DIL:"): dil = line.split(":")[1].strip().lower()
        elif line.startswith("SES:") or line.startswith("FON:") or line.startswith("---"): continue
        
        elif line.startswith("[IMG:"): 
            current_prompt = line.split(":", 1)[1].strip(" ]"); current_type = "image"
        elif line.startswith("[VID:"): 
            current_prompt = line.split(":", 1)[1].strip(" ]"); current_type = "video"
        elif line.startswith("[SFX:"): 
            scenes.append({"type": "sfx", "sfx_prompt": line.split(":", 1)[1].strip(" ]")})
        else: 
            scenes.append({"type": current_type, "img_prompt": current_prompt, "text": line})
            
    return {"channel": kanal, "language": dil, "scenes": scenes}

# --- MOTORLAR ---
def bellek():
    if device=="cuda": torch.cuda.empty_cache(); gc.collect()
def kapa_hepsini():
    global tts, pipe_image, pipe_video, pipe_audio
    tts=None; pipe_image=None; pipe_video=None; pipe_audio=None; bellek()

def yukle_ses():
    global tts
    if tts is None: print("   🔊 TTS Yükleniyor..."); bellek(); tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
def yukle_sfx():
    global pipe_audio
    if pipe_audio is None: kapa_hepsini(); print("   🔊 SFX Yükleniyor..."); pipe_audio = AudioLDMPipeline.from_pretrained("cvssp/audioldm-s-full-v2", torch_dtype=torch.float16).to(device)
def yukle_vid():
    global pipe_video
    if pipe_video is None: kapa_hepsini(); print("   🎥 Video Yükleniyor..."); pipe_video = StableVideoDiffusionPipeline.from_pretrained("stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16").to(device); pipe_video.enable_model_cpu_offload()
def yukle_img(lora=None):
    global pipe_image
    if pipe_image is None:
        kapa_hepsini(); print("   🎨 Resim Yükleniyor...")
        try:
            enc = CLIPVisionModelWithProjection.from_pretrained("h94/IP-Adapter", subfolder="models/image_encoder", torch_dtype=torch.float16).to(device)
            base = "stabilityai/stable-diffusion-xl-base-1.0"
            ckpt = hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors")
            unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(device, torch.float16)
            unet.load_state_dict(load_file(ckpt, device=device))
            pipe_image = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, image_encoder=enc, torch_dtype=torch.float16, variant="fp16").to(device)
            pipe_image.scheduler = EulerDiscreteScheduler.from_config(pipe_image.scheduler.config, timestep_spacing="trailing")
            pipe_image.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter-plus_sdxl_vit-h.safetensors")
            pipe_image.enable_model_cpu_offload()
        except: pass
    if lora: 
        try: pipe_image.unload_lora_weights(); pipe_image.load_lora_weights(os.path.join(lora_folder, lora))
        except: pass
    else: pipe_image.unload_lora_weights()

# --- ÜRETİM ---
def sfx_make(prm, out):
    yukle_sfx()
    if not pipe_audio: return False
    try:
        print(f"   🎵 Efekt: {prm}...")
        au = pipe_audio(prm, num_inference_steps=20, audio_length_in_s=4.0).audios[0]
        import scipy.io.wavfile; scipy.io.wavfile.write(out, 16000, au); return True
    except: return False

def img_make(prm, ch, img_o, vid_o, do_vid, ref_imgs):
    if "black screen" in prm.lower():
        Image.new("RGB", (1024, 576), (0, 0, 0)).save(img_o)
        return True

    lora = "StickFigure_v1_SDXL.safetensors" if ch=="Finans" else None
    yukle_img(lora)
    if not pipe_image: return False
    try:
        print(f"   🎨 Çizim: {prm[:30]}...")
        scl = 0.8 if ch=="Finans" else 0.6
        if not ref_imgs: ref_imgs = [Image.new("RGB",(224,224))]; pipe_image.set_ip_adapter_scale(0.0)
        else: pipe_image.set_ip_adapter_scale(scl)
        
        im = pipe_image(prompt=prm, num_inference_steps=4, guidance_scale=0, ip_adapter_image=ref_imgs).images[0].resize((1024, 576))
        im.save(img_o)
        
        if do_vid:
            print("   🎥 Render...")
            yukle_vid()
            fr = pipe_video(im, decode_chunk_size=2, num_inference_steps=10).frames[0]
            export_to_video(fr, vid_o, fps=7)
        return True
    except Exception as e: print(f"ERR: {e}"); return False

def montaj(dir, clips, aud):
    print("🎬 MONTAJ...")
    v_c = []
    try:
        for c in clips:
            path = c["path"]
            dur = c["duration"] / 1000.0
            if not os.path.exists(path): continue
            
            if path.endswith(".mp4"):
                cl = VideoFileClip(path)
                if cl.duration < dur:
                    # Freeze Frame (Son kareyi dondur)
                    freeze_dur = dur - cl.duration
                    frozen = cl.to_ImageClip(t=cl.duration-0.1).set_duration(freeze_dur)
                    cl = concatenate_videoclips([cl, frozen])
                else:
                    cl = cl.subclip(0, dur)
                v_c.append(cl)
            else:
                v_c.append(ImageClip(path).set_duration(dur).set_fps(24))
        
        fin = concatenate_videoclips(v_c, method="compose")
        fin = fin.set_audio(AudioFileClip(aud))
        fin.write_videofile(os.path.join(dir, "FULL_MOVIE.mp4"), fps=24, preset='ultrafast', threads=4, logger=None)
        print("🎉 FİLM HAZIR!")
        fin.close()
        for x in v_c: x.close()
    except Exception as e: print(f"❌ MONTAJ: {e}")

# --- ANA ---
print("✅ SİSTEM HAZIR!"); yukle_ses()
while True:
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    if not files: time.sleep(1); continue
    f_path = os.path.join(input_folder, files[0]); print(f"\n🎬 {files[0]}")
    time.sleep(0.5)

    try:
        with open(f_path, "r", encoding="utf-8") as f: data = json.load(f)
        ham = data["metin"]; ses = data.get("ses","Ses Yok"); fon = data.get("fon","Yok")

        if "[IMG:" in ham or "[VID:" in ham: plan = manuel_senaryo_coz(ham)
        else:
            d = "en"
            if "DIL:" in ham[:50]: 
                for l in ham.split("\n")[:3]:
                    if "DIL:" in l: d = l.split(":")[1].strip().lower()
            plan = ai_analiz(ham, d)

        if not plan: os.remove(f_path); continue
        ch = plan.get("channel","Genel"); lng = plan.get("language","en"); scn = plan.get("scenes",[])
        if lng not in ['en','tr']: lng = "en"
        cfg = get_kanal(ch); print(f"📺 {cfg['name']} | 🌍 {lng}")

        if not ses.endswith('.wav'): ses += ".wav"
        r_ses = os.path.join(voices_folder, ses)
        if not os.path.exists(r_ses):
            l = [x for x in os.listdir(voices_folder) if x.endswith('wav')]
            if l: r_ses = os.path.join(voices_folder, l[0]); print(f"⚠️ Ses: {l[0]}")
            else: print("❌ Ses Yok"); os.remove(f_path); continue

        p_dir = os.path.join(output_folder, files[0].replace(".json",""))
        os.makedirs(p_dir, exist_ok=True)
        
        mix = AudioSegment.empty(); srt = ""; sn = 1; ms = 0; clips = []
        last_vis = None # Son görseli tut

        for i, s in enumerate(scn):
            tip = s.get("type","image")
            
            # SFX
            if tip == "sfx":
                sf = os.path.join(p_dir, f"{i}_sfx.wav")
                if sfx_make(s.get("sfx_prompt",""), sf):
                    ss = AudioSegment.from_wav(sf) + 5
                    mix += ss
                    
                    vis = last_vis if last_vis else os.path.join(p_dir, "black.png")
                    
                    # DÜZELTİLEN KISIM: son_kareyi_yakala BURADA ÇAĞRILIYOR
                    if vis.endswith(".mp4"):
                        frz = os.path.join(p_dir, f"{i}_freeze.png")
                        if son_kareyi_yakala(vis, frz): vis = frz
                    
                    if not os.path.exists(vis): Image.new("RGB",(1024,576)).save(vis)
                    
                    clips.append({"path": vis, "duration": len(ss)}) 
                    ms += len(ss)
                continue

            # VISUAL
            img = os.path.join(p_dir, f"{i}_img.png"); vid = os.path.join(p_dir, f"{i}_vid.mp4")
            do_vid = (tip=="video" and cfg['vid'])
            
            refs = []
            if ch == "Finans":
                rd = os.path.join(ref_folder, "copadam.png")
                if os.path.exists(rd): refs.append(load_image(rd))
            
            img_make(s.get("img_prompt",""), ch, img, vid, do_vid, refs)
            vis = vid if (do_vid and os.path.exists(vid)) else img
            last_vis = vis

            # AUDIO
            txt = ceviri_yap(s.get("text",""), lng)
            print(f"   🗣️ {txt[:20]}...")
            wav = os.path.join(p_dir, f"{i}_aud.wav")
            yukle_ses()
            
            tts.tts_to_file(text=txt, speaker_wav=r_ses, language=lng, file_path="temp.wav", split_sentences=False, speed=1.0, temperature=0.75, repetition_penalty=1.0)
            
            seg = sesi_temizle(AudioSegment.from_wav("temp.wav"))
            seg.export(wav, format="wav")
            
            dur = len(seg) + 200
            srt += f"{sn}\n{srt_zamani(ms/1000)} --> {srt_zamani((ms+dur)/1000)}\n{txt}\n\n"; sn+=1
            mix += seg + AudioSegment.silent(duration=200)
            clips.append({"path": vis, "duration": dur})
            ms += dur

        # FON
        if fon != "Yok":
            print("🎹 Fon...")
            for e in [".mp3", ".wav"]:
                fp = os.path.join(ambience_folder, fon+e)
                if os.path.exists(fp):
                    bg = AudioSegment.from_file(fp) - 25
                    while len(bg) < len(mix) + 2000: bg += bg
                    mix = bg[:len(mix)+1000].fade_out(3000).overlay(mix)
                    break
        
        f_wav = os.path.join(p_dir, "FINAL.wav")
        mix.export(f_wav, format="wav")
        with open(os.path.join(p_dir, "SUB.srt"), "w", encoding="utf-8") as f: f.write(srt)
        
        montaj(p_dir, clips, f_wav)
        
        print(f"✅ BİTTİ: {p_dir}")
        os.remove(f_path)
        if os.path.exists("temp.wav"): os.remove("temp.wav")

    except Exception as e:
        print(f"❌ HATA: {e}"); 
        if os.path.exists(f_path): os.remove(f_path)