import os
from moviepy.editor import VideoFileClip, concatenate_videoclips

# --- AYARLAR ---
print("\n==================================================")
print(">>> MEGA VİDEO BİRLEŞTİRİCİ <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
output_folder = os.path.join(base_path, "Tamamlananlar")
mega_folder = os.path.join(base_path, "MEGA_CIKTILAR")
os.makedirs(mega_folder, exist_ok=True)

def videolari_bul_ve_birlestir():
    # Tamamlananlar klasöründeki tüm alt klasörleri tara
    video_dosyalari = []
    
    # Klasörleri tarihe göre veya isme göre sırala (SERI_ID sayesinde sırasıyla gelir)
    projeler = sorted(os.listdir(output_folder))
    
    print("📂 Bulunan Parçalar:")
    for proje in projeler:
        proje_yolu = os.path.join(output_folder, proje)
        if os.path.isdir(proje_yolu):
            video_path = os.path.join(proje_yolu, "FULL_MOVIE.mp4")
            if os.path.exists(video_path):
                # Sadece bizim SERİ üretimi olanları al (İsmi SERI_ ile başlayanlar)
                if "SERI_" in proje:
                    print(f"   ➕ Eklendi: {proje}")
                    video_dosyalari.append(VideoFileClip(video_path))
    
    if not video_dosyalari:
        print("❌ Birleştirilecek 'SERI_' videosu bulunamadı.")
        return

    print(f"\n🏗️ {len(video_dosyalari)} video birleştiriliyor... (Bu işlem biraz sürer)")
    
    # Hepsini uc uca ekle
    final_clip = concatenate_videoclips(video_dosyalari, method="compose")
    
    # Kaydet
    cikti_adi = os.path.join(mega_folder, f"1_SAATLIK_MEGA_VIDEO_{int(os.time.time())}.mp4")
    final_clip.write_videofile(cikti_adi, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
    
    print(f"\n✅✅✅ TEBRİKLER! VİDEO HAZIR: {cikti_adi}")
    
    # Temizlik (İsteğe bağlı: Klipleri kapat)
    for v in video_dosyalari: v.close()

if __name__ == "__main__":
    videolari_bul_ve_birlestir()