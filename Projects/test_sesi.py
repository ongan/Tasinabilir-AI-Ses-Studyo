import os
import torch
from TTS.api import TTS

# --- BÖLÜM 1: AKILLI DONANIM SEÇİMİ ---
# Burası diğer laptoplarda da çalışmasını sağlayan kısım.
# Eğer NVIDIA ekran kartı varsa 'cuda' seçer, yoksa 'cpu' işlemciyi seçer.
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n==================================================")
print(f"SİSTEM BİLGİSİ: İşlem şu donanım üzerinde yapılacak: ---> {device.upper()} <---")
if device == "cuda":
    print("Harika! RTX ekran kartının gücü kullanılıyor.")
else:
    print("Dikkat: Ekran kartı bulunamadı, işlemci (CPU) kullanılıyor. Biraz yavaş olabilir.")
print(f"==================================================\n")


# --- BÖLÜM 2: MODELİ HAZIRLA ---
print("XTTS Modeli yükleniyor... (İlk çalıştırmada indirme yapacağı için biraz sürebilir, sabret.)")
# Ses klonlama ustası XTTS v2 modelini başlatıyoruz.
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)


# --- BÖLÜM 3: SES ÜRETİM AYARLARI ---
metin = "Merhaba! Ben senin yeni taşınabilir yapay zeka asistanınım. Bu sesi, harici disk üzerindeki RTX destekli sistemden üretiyorum. Kurulum başarıyla tamamlandı!"
kayit_yeri = "ilk_basarili_ses.wav"

# Şimdilik klonlama yapmıyoruz, modelin içindeki hazır bir sesi kullanıyoruz.
# Daha sonra buraya kendi ses dosyamızı vereceğiz.
konusmaci = "Ana Florence" 

print(f"\nSes üretiliyor... Lütfen bekleyin.")


# --- BÖLÜM 4: ÇALIŞTIR VE KAYDET ---
tts.tts_to_file(
    text=metin,
    speaker=konusmaci,
    language="tr", # Türkçe konuşması için 'tr' seçtik.
    file_path=kayit_yeri,
    split_sentences=True
)

print(f"\n>>> BAŞARILI! Ses dosyası şuraya kaydedildi: {kayit_yeri} <<<")
# Dosyayı otomatik olarak bulunduğumuz klasöre (Projects içine) kaydedecek.