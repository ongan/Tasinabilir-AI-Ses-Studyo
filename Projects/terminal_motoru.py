import torch
import os
import gc
import time
from TTS.api import TTS
from pydub import AudioSegment

# --- 1. AYARLAR ---
print("\n==================================================")
print("     TERMINAL SES MOTORU (ARAYÜZSÜZ)")
print("==================================================\n")

simdiki_klasor = os.getcwd() 
ana_klasor = os.path.dirname(simdiki_klasor)
# FFmpeg yolunu elle gösteriyoruz (Sorun burada olabilir)
ffmpeg_yolu = os.path.join(ana_klasor, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
ses_kutuphanesi = os.path.join(simdiki_klasor, "Voices") 

print(f"FFmpeg Yolu Kontrolü: {ffmpeg_yolu}")
if os.path.exists(ffmpeg_yolu):
    print("✅ FFmpeg bulundu.")
else:
    print("❌ HATA: FFmpeg bulunamadı! Pydub çalışmayacak.")
    # Exit yapmıyorum, hatayı görelim.

AudioSegment.converter = ffmpeg_yolu

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- 2. MODEL YÜKLEME ---
print("Model Yükleniyor...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print("✅ Model Hazır.\n")

# --- 3. TEST VERİLERİ ---
# O takılan metni buraya gömüyoruz.
test_metni = """
Bak evlat. Deden ölünce ben büyümek zorunda kaldım.
Aile çökerken omuz aradılar.
Beni büyük yapan yükü kaldırmak zorunda kalışım oldu.
Mavi balina öldüğünde dibe çöker.
"""

# Referans ses (Klasörde referans.wav olduğundan emin ol)
# Eğer yoksa kod hata verir.
referans_ses = "referans.wav" 
ref_yol = os.path.join(simdiki_klasor, referans_ses)

if not os.path.exists(ref_yol):
    print(f"❌ HATA: '{referans_ses}' dosyası Projects klasöründe yok!")
    print("Lütfen çalışan bir ses dosyasının adını 'referans.wav' yapıp yanına koy.")
    exit()

# --- 4. İŞLEM DÖNGÜSÜ ---
print("--- İŞLEM BAŞLIYOR ---")

# Basit bölme
cumleler = [c.strip() for c in test_metni.split(".") if len(c.strip()) > 1]
print(f"İşlenecek Cümle Sayısı: {len(cumleler)}")

birlestirilmis_ses = AudioSegment.empty()
temp_dosya = "temp_terminal.wav"

for i, cumle in enumerate(cumleler):
    print(f"\n[{i+1}/{len(cumleler)}] Şu cümle işleniyor: {cumle}")
    
    try:
        # VRAM Temizliği
        if device == "cuda":
            torch.cuda.empty_cache()
            gc.collect()
        
        start = time.time()
        # ÜRETİM
        tts.tts_to_file(
            text=cumle,
            speaker_wav=ref_yol,
            language="tr",
            file_path=temp_dosya,
            split_sentences=False
        )
        end = time.time()
        print(f"   -> Ses üretildi ({end-start:.2f} sn). Birleştiriliyor...")
        
        # BİRLEŞTİRME (Sorun çıkaran yer burası olabilir)
        parca = AudioSegment.from_wav(temp_dosya)
        birlestirilmis_ses += parca + AudioSegment.silent(duration=250)
        print("   -> Birleştirme tamam.")
        
    except Exception as e:
        print(f"❌ HATA OLUŞTU: {e}")
        # Hatayı tam görelim
        import traceback
        traceback.print_exc()

# --- 5. KAYIT ---
cikti_adi = "terminal_sonuc.wav"
print(f"\nDosya kaydediliyor: {cikti_adi} ...")
try:
    birlestirilmis_ses.export(cikti_adi, format="wav")
    print("✅✅✅ İŞLEM BAŞARIYLA BİTTİ! ✅✅✅")
except Exception as e:
    print(f"❌ KAYIT HATASI (FFmpeg sorunu olabilir): {e}")

if os.path.exists(temp_dosya):
    os.remove(temp_dosya)