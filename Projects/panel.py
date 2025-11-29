import gradio as gr
import torch
import os
import re
import gc
import shutil
import sys
from TTS.api import TTS
from pydub import AudioSegment

# --- PATH VE AYARLAR ---
simdiki_klasor = os.getcwd() 
ana_klasor = os.path.dirname(simdiki_klasor)
ffmpeg_yolu = os.path.join(ana_klasor, "Tools", "ffmpeg", "bin", "ffmpeg.exe")
ses_kutuphanesi = os.path.join(simdiki_klasor, "Voices") 

# Ses kütüphanesi klasörünü oluştur
os.makedirs(ses_kutuphanesi, exist_ok=True)

# FFmpeg ayarı
AudioSegment.converter = ffmpeg_yolu

# Donanım seçimi
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"SİSTEM: {device.upper()} modunda çalışıyor.")

# Modeli Yükle
print("Model Yükleniyor... (Bu islem biraz sürebilir)")
try:
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print(">>> Model Başarıyla Yüklendi! <<<")
except Exception as e:
    print(f"MODEL YÜKLEME HATASI: {e}")
    input("Kapatmak için Enter'a bas...")
    sys.exit()

# --- YARDIMCI FONKSİYONLAR ---

def sesleri_listele():
    """Voices klasöründeki ses dosyalarını listeler."""
    if not os.path.exists(ses_kutuphanesi):
        return ["Henüz ses yüklenmedi"]
    dosyalar = [f for f in os.listdir(ses_kutuphanesi) if f.endswith(('.wav', '.mp3', '.m4a'))]
    return dosyalar if dosyalar else ["Henüz ses yüklenmedi"]

def sesi_kutuphaneye_kaydet(dosya, isim):
    """Yeni yüklenen sesi kütüphaneye kopyalar."""
    if dosya is None:
        return gr.Dropdown(choices=sesleri_listele()), "Lütfen bir dosya seçin."
    
    # Dosya adını belirle
    hedef_isim = isim if isim else os.path.basename(dosya.name)
    if not hedef_isim.endswith(('.wav', '.mp3')):
        hedef_isim += ".wav"
        
    hedef_yol = os.path.join(ses_kutuphanesi, hedef_isim)
    shutil.copy(dosya.name, hedef_yol)
    
    return gr.Dropdown(choices=sesleri_listele(), value=hedef_isim), f"'{hedef_isim}' kütüphaneye eklendi!"

def sesi_sil(secilen_ses):
    """Seçili sesi kütüphaneden siler."""
    if not secilen_ses or secilen_ses == "Henüz ses yüklenmedi":
        return gr.Dropdown(choices=sesleri_listele()), "Silinecek dosya seçilmedi."
    
    yol = os.path.join(ses_kutuphanesi, secilen_ses)
    if os.path.exists(yol):
        os.remove(yol)
        yeni_liste = sesleri_listele()
        yeni_deger = yeni_liste[0] if yeni_liste and yeni_liste[0] != "Henüz ses yüklenmedi" else None
        return gr.Dropdown(choices=yeni_liste, value=yeni_deger), f"'{secilen_ses}' silindi."
    else:
        return gr.Dropdown(choices=sesleri_listele()), "Dosya bulunamadı."

def metni_temizle_ve_bol(metin, virgul_yoksay):
    metin = metin.replace("\n", " ").replace("\r", " ").replace(" ", " ")
    metin = " ".join(metin.split())

    if virgul_yoksay:
        metin = metin.replace(",", "") 

    ilk_bolum = re.split(r'(?<=[.!?])\s+', metin)
    final_cumleler = []
    
    for cumle in ilk_bolum:
        if not cumle.strip():
            continue
        if len(cumle) > 500:
            alt_parcalar = re.split(r'(?<=[;])\s+', cumle)
            final_cumleler.extend(alt_parcalar)
        else:
            final_cumleler.append(cumle)
    return final_cumleler

def ses_uret(metin, secilen_ses_adi, dil, hiz, es_suresi, virgul_yoksay, progress=gr.Progress()):
    if not secilen_ses_adi or secilen_ses_adi == "Henüz ses yüklenmedi":
        return None, "Lütfen listeden geçerli bir ses seçin!"
        
    referans_ses = os.path.join(ses_kutuphanesi, secilen_ses_adi)
    
    if not os.path.exists(referans_ses):
        return None, "Seçilen ses dosyası bulunamadı!"

    cumleler = metni_temizle_ve_bol(metin, virgul_yoksay)
    toplam_cumle = len(cumleler)
    
    print(f"\nToplam {toplam_cumle} parça işlenecek. Referans: {secilen_ses_adi}")

    birlestirilmis_ses = AudioSegment.empty()
    temp_dosya = "gecici_parca.wav"
    sonuc_dosyasi = "tamamlanmis_hikaye.wav"

    try:
        for i, cumle in enumerate(cumleler):
            progress((i / toplam_cumle), desc=f"Okunuyor: {i+1}/{toplam_cumle}")
            
            temiz_cumle = cumle.strip()
            if len(temiz_cumle) < 2: continue

            if device == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            tts.tts_to_file(
                text=temiz_cumle,
                speaker_wav=referans_ses,
                language=dil,
                file_path=temp_dosya,
                split_sentences=False, 
                speed=hiz
            )

            parca = AudioSegment.from_wav(temp_dosya)
            birlestirilmis_ses += parca + AudioSegment.silent(duration=es_suresi)

        birlestirilmis_ses.export(sonuc_dosyasi, format="wav")
        if os.path.exists(temp_dosya): os.remove(temp_dosya)

        return sonuc_dosyasi, f"Başarılı! Kayıt: {sonuc_dosyasi}"

    except Exception as e:
        print(f"HATA: {e}")
        return None, f"Hata: {str(e)}"

# --- ARAYÜZ ---
with gr.Blocks(title="AI Studio Pro v3") as demo:
    gr.Markdown("# 🎙️ AI Ses Stüdyosu - Pro Panel")
    gr.Markdown(f"**Mod:** {device.upper()} | Ses Kütüphanesi & Gelişmiş Ayarlar")
    
    with gr.Row():
        with gr.Column(scale=1):
            giris_metni = gr.Textbox(label="Metin / Hikaye", lines=10, placeholder="Metni buraya yapıştırın...")
            
            gr.Markdown("### 📂 Ses Kütüphanesi")
            with gr.Group():
                ses_listesi = gr.Dropdown(label="Kullanılacak Sesi Seçin", choices=sesleri_listele(), value=None, interactive=True)
                
                with gr.Row():
                    yeni_ses_dosyasi = gr.File(label="Yeni Ses Ekle", file_count="single", file_types=[".wav", ".mp3"])
                    yeni_ses_adi = gr.Textbox(label="Kaydedilecek İsim (Opsiyonel)", placeholder="Örn: Benim Sesim")
                
                with gr.Row():
                    kaydet_btn = gr.Button("💾 Kütüphaneye Kaydet", variant="secondary")
                    sil_btn = gr.Button("🗑️ Seçili Sesi Sil", variant="stop")
            
            gr.Markdown("### ⚙️ İnce Ayarlar")
            with gr.Row():
                dil_secimi = gr.Dropdown(label="Dil", choices=["tr", "en", "es", "fr", "de"], value="tr")
                hiz_ayari = gr.Slider(label="Okuma Hızı", minimum=0.7, maximum=1.5, value=1.0, step=0.1)
            
            with gr.Row():
                es_suresi = gr.Slider(label="Cümle Arası Es (ms)", minimum=0, maximum=2000, value=250, step=50)
                virgul_kutusu = gr.Checkbox(label="Virgülleri Yoksay", value=False)
            
            uret_buton = gr.Button("▶️ Sesi Oluştur", variant="primary")
        
        with gr.Column(scale=1):
            ses_cikti = gr.Audio(label="Sonuç Dosyası", type="filepath")
            durum_mesaji = gr.Label(label="Sistem Mesajı")

    # Aksiyonlar
    kaydet_btn.click(
        fn=sesi_kutuphaneye_kaydet,
        inputs=[yeni_ses_dosyasi, yeni_ses_adi],
        outputs=[ses_listesi, durum_mesaji]
    )
    
    sil_btn.click(
        fn=sesi_sil,
        inputs=[ses_listesi],
        outputs=[ses_listesi, durum_mesaji]
    )
    
    uret_buton.click(
        fn=ses_uret, 
        inputs=[giris_metni, ses_listesi, dil_secimi, hiz_ayari, es_suresi, virgul_kutusu], 
        outputs=[ses_cikti, durum_mesaji]
    )

# --- BAŞLATMA KODU (HATA YAKALAYICILI) ---
if __name__ == "__main__":
    try:
        print("\n========================================================")
        print(" Web Arayüzü Başlatılıyor... http://127.0.0.1:7860")
        print("========================================================\n")
        demo.launch(inbrowser=True)
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"KRİTİK HATA OLUŞTU: {e}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        input("Hatayı okuduysan kapatmak için Enter'a bas...")