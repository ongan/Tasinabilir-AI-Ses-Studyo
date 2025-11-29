import torch
import os
import time
import json
import gc
import re
from TTS.api import TTS
from pydub import AudioSegment, effects

# --- DÜZELTİLMİŞ AYARLAR (YOL SORUNU ÇÖZÜLDÜ) ---
print(">>> PRO MOTOR BAŞLATILIYOR (V5.1 - PATH FIX) <<<")

# os.getcwd() yerine dosyanın kendi konumunu alıyoruz
base_path = os.path.dirname(os.path.abspath(__file__)) 

input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")

# FFmpeg Yolu (Bir üst klasördeki Tools)
tools_path = os.path.dirname(base_path) 
ffmpeg_bin = os.path.join(tools_path, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
AudioSegment.converter = ffmpeg_bin

# FFmpeg Yolu
tools_path = os.path.dirname(base_path)
ffmpeg_bin = os.path.join(tools_path, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
AudioSegment.converter = ffmpeg_bin

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- MODEL YÜKLEME ---
print("Model Yükleniyor... (Stabilite ayarları aktif)")
try:
    # gpu=True bazen kilitlenmeyi engeller
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True).to(device)
    print("✅ MOTOR HAZIR! İŞ BEKLENİYOR...")
except Exception as e:
    print(f"HATA: {e}")
    time.sleep(10)
    exit()

def metni_temizle(ham_metin):
    # XTTS'in sevmediği karakterleri temizle
    temiz = ham_metin.replace("—", ", ").replace("…", ".").replace("\n", " ")
    # Sadece izin verilen karakterler kalsın (Harfler, rakamlar, temel noktalama)
    # Bu regex Türkçe karakterleri korur
    return " ".join(temiz.split())

while True:
    # 1. JSON işlerini tara
    files = [f for f in os.listdir(input_folder) if f.endswith(".json")]
    
    if len(files) > 0:
        json_file = files[0]
        print(f"\n--- YENİ İŞ ALINDI: {json_file} ---")
        
        try:
            # İş dosyasını oku
            with open(os.path.join(input_folder, json_file), "r", encoding="utf-8") as f:
                data = json.load(f)
            
            metin_govde = data["metin"]
            ses_adi = data.get("ses", "Ses Yok")
            fon_adi = data.get("fon", "Yok") # Fon müziği isteği
            
            # Yolları hazırla
            if not ses_adi.endswith(('.wav', '.mp3')): ses_adi += ".wav"
            ref_path = os.path.join(voices_folder, ses_adi)
            
            if not os.path.exists(ref_path):
                print(f"❌ HATA: Referans ses bulunamadı ({ses_adi}). İş iptal.")
                os.remove(os.path.join(input_folder, json_file))
                continue

            # --- SES ÜRETİM AŞAMASI ---
            print(f"🎤 Seslendirmen: {ses_adi}")
            print(f"🎵 Fon Müziği: {fon_adi}")
            
            # Metni hazırla
            temiz_metin = metni_temizle(metin_govde)
            cumleler = [c.strip() for c in temiz_metin.split(".") if len(c.strip()) > 1]
            print(f"Toplam Cümle: {len(cumleler)}")
            
            konusma_sesi = AudioSegment.empty()
            temp_wav = "temp_worker.wav"
            
            for i, cumle in enumerate(cumleler):
                print(f"[{i+1}] İşleniyor: {cumle[:30]}...")
                
                if device == "cuda":
                    torch.cuda.empty_cache()
                    gc.collect()
                
                # KALİTE AYARLARI (Burada kekelemeyi önlüyoruz)
                tts.tts_to_file(
                    text=cumle,
                    speaker_wav=ref_path,
                    language="tr",
                    file_path=temp_wav,
                    split_sentences=False,
                    temperature=0.65,      # (Varsayılan 0.75) Düşürdükçe daha stabil okur, saçmalamaz.
                    repetition_penalty=2.0, # (Varsayılan 1.0) Tekrarları engeller (olururur sorunu için).
                    length_penalty=1.0,     # Cümle uzunluğunu dengeler.
                    speed=1.0
                )
                
                parca = AudioSegment.from_wav(temp_wav)
                konusma_sesi += parca + AudioSegment.silent(duration=250)
            
            # --- FON MÜZİĞİ EKLEME AŞAMASI ---
            final_audio = konusma_sesi # Varsayılan olarak sadece konuşma
            
            if fon_adi and fon_adi != "Yok":
                # Fon dosyası arama (.mp3 veya .wav olabilir)
                fon_yolu = None
                for ext in [".mp3", ".wav"]:
                    potansiyel = os.path.join(ambience_folder, fon_adi + ext)
                    if os.path.exists(potansiyel):
                        fon_yolu = potansiyel
                        break
                
                if fon_yolu:
                    print("🎹 Ambiyans ekleniyor...")
                    fon_muzigi = AudioSegment.from_file(fon_yolu)
                    
                    # 1. Ses seviyesini düşür (Ducking) - Arkada kalsın
                    fon_muzigi = fon_muzigi - 18 # 18 dB kısıyoruz
                    
                    # 2. Döngü (Loop) - Konuşma bitene kadar müzik devam etsin
                    while len(fon_muzigi) < len(konusma_sesi) + 2000:
                        fon_muzigi += fon_muzigi
                        
                    # 3. Süreyi eşitle (Konuşma süresi + 1 saniye pay)
                    fon_muzigi = fon_muzigi[:len(konusma_sesi) + 1000]
                    
                    # 4. Fade Out (Müzik sonunda yavaşça kısılsın)
                    fon_muzigi = fon_muzigi.fade_out(2000)
                    
                    # 5. Birleştir (Overlay)
                    final_audio = fon_muzigi.overlay(konusma_sesi)
                else:
                    print(f"⚠️ Uyarı: Fon müziği dosyası bulunamadı ({fon_adi}). Sadece ses kaydedilecek.")

            # --- KAYIT ---
            out_name = json_file.replace(".json", ".wav")
            out_path = os.path.join(output_folder, out_name)
            
            # Normalize et (Ses patlamalarını önle)
            final_audio = effects.normalize(final_audio)
            
            final_audio.export(out_path, format="wav")
            print(f"✅ BİTTİ: {out_name}")
            
            # Temizlik
            os.remove(os.path.join(input_folder, json_file))
            if os.path.exists(temp_wav): os.remove(temp_wav)
            
        except Exception as e:
            print(f"❌ HATA: {e}")
            if os.path.exists(os.path.join(input_folder, json_file)):
                os.remove(os.path.join(input_folder, json_file))
    
    else:
        time.sleep(1)