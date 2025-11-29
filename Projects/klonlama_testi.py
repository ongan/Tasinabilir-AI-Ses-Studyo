import os
import torch
from TTS.api import TTS

# 1. Donanım Ayarı (Klasik kontrolümüz)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"İşlem birimi: {device}")

# 2. Modeli Yükle
# Modeli zaten indirdiği için bu sefer beklemeden açılacak.
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

# 3. Klonlama Ayarları
# Buraya konuşturmak istediğin metni yaz.
metin = """
    Merhaba! Şu anda duyduğun bu ses, aslında gerçek bir insana ait değil. 
    Benim sesimden klonlanmış yapay bir zeka. 
    Sence de biraz ürkütücü ama aynı zamanda büyüleyici değil mi?
    Artık seninle dilediğimiz kadar video içeriği üretebiliriz.
"""

# Senin klasöre attığın dosyanın adı.
ornek_ses_dosyasi = "referans.wav" 
cikti_dosyasi = "klonlanmis_ses.wav"

# 4. Üretim (Sihir burada gerçekleşiyor)
print("Ses klonlanıyor... (Referans sesten tonlama analizi yapılıyor)")

tts.tts_to_file(
    text=metin,
    speaker_wav=ornek_ses_dosyasi, # BURASI ÖNEMLİ: Hazır isim değil, dosya yolu veriyoruz.
    language="tr",
    file_path=cikti_dosyasi,
    split_sentences=True
)

print(f"Tamamlandı! '{cikti_dosyasi}' adıyla kaydedildi.")