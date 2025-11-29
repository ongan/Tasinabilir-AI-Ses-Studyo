import gradio as gr
import torch
import os
import gc
import shutil
import time
from TTS.api import TTS
from pydub import AudioSegment

# --- 1. AYARLAR ---
print("\n--- ARAYÜZ MOTORU BAŞLATILIYOR ---")
simdiki_klasor = os.getcwd() 
ana_klasor = os.path.dirname(simdiki_klasor)
ffmpeg_yolu = os.path.join(ana_klasor, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
ses_kutuphanesi = os.path.join(simdiki_klasor, "Voices") 

os.makedirs(ses_kutuphanesi, exist_ok=True)
AudioSegment.converter = ffmpeg_yolu

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Donanım: {device}")

# --- 2. MODELİ YÜKLE ---
print("Model Yükleniyor...")
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print(">>> MODEL HAZIR! <<<")
except Exception as e:
    print(f"Model Hatası: {e}")
    exit()

# --- 3. YARDIMCI FONKSİYONLAR ---

def liste_yenile():
    if not os.path.exists(ses_kutuphanesi): return ["Ses Yok"]
    dosyalar = [f for f in os.listdir(ses_kutuphanesi) if f.endswith(('.wav', '.mp3'))]
    return dosyalar if dosyalar else ["Ses Yok"]

def ses_kaydet(dosya, isim):
    if dosya is None: return gr.Dropdown(choices=liste_yenile()), "Dosya yok!"
    hedef = isim if isim else os.path.basename(dosya.name)
    if not hedef.endswith(('.wav', '.mp3')): hedef += ".wav"
    shutil.copy(dosya.name, os.path.join(ses_kutuphanesi, hedef))
    return gr.Dropdown(choices=liste_yenile(), value=hedef), f"Kaydedildi: {hedef}"

def motoru_calistir(metin, secilen_ses):
    """
    Bu fonksiyon terminal_motoru.py ile BİREBİR AYNI mantıkta çalışır.
    """
    print("\n--- ARAYÜZDEN İŞLEM TETİKLENDİ ---")
    
    if not secilen_ses or secilen_ses == "Ses Yok": 
        return None, "Lütfen bir ses seçin!"
    
    ref_yol = os.path.join(ses_kutuphanesi, secilen_ses)
    if not os.path.exists(ref_yol):
        return None, "Ses dosyası bulunamadı!"

    # --- TEMİZLİK VE BÖLME (Terminal Koduyla Aynı) ---
    # Uzun tire sorununu manuel çözüyoruz
    islenen_metin = metin.replace("—", ", ").replace("\n", " ")
    
    # Sadece noktadan bölüyoruz (En güvenli yöntem)
    parcalar = islenen_metin.split(".")
    cumleler = [c.strip() for c in parcalar if len(c.strip()) > 1]
    
    toplam = len(cumleler)
    print(f"Toplam Cümle: {toplam}")

    birlestirilmis = AudioSegment.empty()
    temp = "temp_gui.wav"
    sonuc = "sonuc_final.wav"
    
    yield None, "İşlem Başlıyor..." # Arayüze ilk sinyal

    for i, cumle in enumerate(cumleler):
        mesaj = f"İşleniyor [{i+1}/{toplam}]: {cumle[:30]}..."
        print(mesaj)
        yield None, mesaj # Arayüze bilgi gönder

        try:
            if device == "cuda":
                torch.cuda.empty_cache()
                gc.collect()
            
            # ÜRETİM
            tts.tts_to_file(
                text=cumle,
                speaker_wav=ref_yol,
                language="tr",
                file_path=temp,
                split_sentences=False
            )
            
            # BİRLEŞTİRME
            parca = AudioSegment.from_wav(temp)
            birlestirilmis += parca + AudioSegment.silent(duration=250)
            
        except Exception as e:
            print(f"HATA (Atlandı): {e}")

    # KAYIT
    print("Dosya kaydediliyor...")
    birlestirilmis.export(sonuc, format="wav")
    
    yield sonuc, "✅ İŞLEM TAMAMLANDI!"

# --- 4. ARAYÜZ ---
with gr.Blocks(title="FİNAL PANEL") as demo:
    gr.Markdown("## 🎙️ AI Ses Stüdyosu (Final)")
    
    with gr.Row():
        with gr.Column():
            txt_giris = gr.Textbox(label="Hikaye Metni", lines=8, placeholder="Metni buraya yapıştırın...")
            
            with gr.Group():
                gr.Markdown("### 1. Ses Yükle")
                with gr.Row():
                    upl_file = gr.File(file_count="single")
                    upl_name = gr.Textbox(placeholder="Sesin Adı")
                    btn_save = gr.Button("Kaydet")
            
            with gr.Group():
                gr.Markdown("### 2. Sesi Seç ve Üret")
                dd_ses = gr.Dropdown(label="Kayıtlı Sesler", choices=liste_yenile(), interactive=True)
                btn_run = gr.Button("SESİ OLUŞTUR", variant="primary")
                
        with gr.Column():
            lbl_info = gr.Label(label="Durum")
            audio_out = gr.Audio(label="Sonuç Dosyası")

    # Olaylar
    btn_save.click(fn=ses_kaydet, inputs=[upl_file, upl_name], outputs=[dd_ses, lbl_info])
    
    # DİKKAT: Burada queue kullanıyoruz ki arayüz donmasın
    btn_run.click(
        fn=motoru_calistir,
        inputs=[txt_giris, dd_ses],
        outputs=[audio_out, lbl_info]
    )

if __name__ == "__main__":
    # queue() ekledik, bu işlem sırasında arayüzün yanıt vermesini sağlar
    demo.queue().launch(inbrowser=True)