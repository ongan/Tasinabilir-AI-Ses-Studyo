import gradio as gr
import torch
import os
import re
import gc
from TTS.api import TTS
from pydub import AudioSegment

# --- PATH VE AYARLAR ---
simdiki_klasor = os.getcwd() 
ana_klasor = os.path.dirname(simdiki_klasor)
ffmpeg_yolu = os.path.join(ana_klasor, "Tools", "ffmpeg", "bin", "ffmpeg.exe")

# FFmpeg yolunu pydub'a göster
AudioSegment.converter = ffmpeg_yolu

# Donanım seçimi
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"==================================================")
print(f"SİSTEM: {device.upper()} modunda çalışıyor.")
print(f"==================================================")

# Modeli Yükle
print("Yapay Zeka Modeli Başlatılıyor...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print(">>> Model Hazır! <<<")

def metni_temizle_ve_bol(metin):
    """
    Metni yapay zeka için sindirilebilir parçalara ayırır.
    """
    # 1. Metin Temizliği (Satır atlamaları ve garip boşlukları sil)
    metin = metin.replace("\n", " ").replace("\r", " ").replace(" ", " ")
    metin = " ".join(metin.split()) # Çift boşlukları teke indir

    # 2. Önce Cümlelere Böl (. ! ? ve sonrasında boşluk varsa)
    ilk_bolum = re.split(r'(?<=[.!?])\s+', metin)
    
    final_cumleler = []
    
    # 3. Çok uzun cümleleri kontrol et
    for cumle in ilk_bolum:
        if not cumle.strip():
            continue
            
        # Eğer bir cümle 250 karakterden uzunsa, onu virgüllerden de bölmeye çalış
        if len(cumle) > 250:
            alt_parcalar = re.split(r'(?<=[,;])\s+', cumle)
            final_cumleler.extend(alt_parcalar)
        else:
            final_cumleler.append(cumle)
            
    return final_cumleler

def ses_uret(metin, referans_ses, dil, hiz, progress=gr.Progress()):
    if not metin or not referans_ses:
        return None, "Lütfen metin ve referans ses dosyası girin!"

    # Metni işle
    cumleler = metni_temizle_ve_bol(metin)
    toplam_cumle = len(cumleler)
    
    print(f"\nİşlenecek toplam parça sayısı: {toplam_cumle}")

    if toplam_cumle == 0:
        return None, "Metin ayrıştırılamadı."

    birlestirilmis_ses = AudioSegment.empty()
    temp_dosya = "gecici_parca.wav"
    sonuc_dosyasi = "tamamlanmis_hikaye.wav"

    try:
        for i, cumle in enumerate(cumleler):
            # İlerleme çubuğunu güncelle
            progress((i / toplam_cumle), desc=f"İşleniyor: {i+1}/{toplam_cumle}")
            
            # Konsola ne işlediğimizi yazalım (Takılırsa nerede takıldığını görelim)
            temiz_cumle = cumle.strip()
            if len(temiz_cumle) < 2: # 1-2 harflik hatalı parçaları atla
                continue
                
            print(f"[{i+1}/{toplam_cumle}] İşleniyor: {temiz_cumle[:50]}...")

            # --- BELLEK TEMİZLİĞİ (KRİTİK NOKTA) ---
            # Her cümlede VRAM'i rahatlat ki takılmasın
            if device == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            # Sesi üret
            tts.tts_to_file(
                text=temiz_cumle,
                speaker_wav=referans_ses,
                language=dil,
                file_path=temp_dosya,
                split_sentences=False, # Biz zaten böldük
                speed=hiz
            )

            # Sesi ekle
            parca = AudioSegment.from_wav(temp_dosya)
            # Cümleler arasına biraz nefes payı (es) koy (350ms)
            birlestirilmis_ses += parca + AudioSegment.silent(duration=350)

        # Hepsini kaydet
        print("Birleştiriliyor ve kaydediliyor...")
        birlestirilmis_ses.export(sonuc_dosyasi, format="wav")
        
        # Temizlik
        if os.path.exists(temp_dosya):
            os.remove(temp_dosya)

        return sonuc_dosyasi, f"Bitti! {toplam_cumle} parça birleştirildi."

    except Exception as e:
        print(f"HATA OLUŞTU: {e}")
        return None, f"Bir hata oluştu: {str(e)}"

# --- ARAYÜZ ---
with gr.Blocks(title="AI Profesyonel Seslendirici") as demo:
    gr.Markdown("# 🎙️ Profesyonel Uzun Metin Seslendirici")
    gr.Markdown(f"**Mod:** {device.upper()} | **Durum:** Bellek Korumalı & Akıllı Bölücü Aktif")
    
    with gr.Row():
        with gr.Column():
            giris_metni = gr.Textbox(label="Hikaye / Metin", lines=12, placeholder="Metni yapıştırın...")
            ref_ses_input = gr.Audio(label="Klonlanacak Ses", type="filepath")
            
            with gr.Row():
                dil_secimi = gr.Dropdown(label="Dil", choices=["tr", "en", "es", "fr", "de"], value="tr")
                hiz_ayari = gr.Slider(label="Okuma Hızı", minimum=0.7, maximum=1.5, value=1.0, step=0.1)
            
            uret_buton = gr.Button("Sesi Oluştur (Başlat)", variant="primary")
        
        with gr.Column():
            ses_cikti = gr.Audio(label="Sonuç Dosyası")
            durum_mesaji = gr.Label(label="İşlem Durumu")

    uret_buton.click(
        fn=ses_uret, 
        inputs=[giris_metni, ref_ses_input, dil_secimi, hiz_ayari], 
        outputs=[ses_cikti, durum_mesaji]
    )

demo.launch(inbrowser=True)