import gradio as gr
import os
import json
import time
import shutil

# --- AYARLAR ---
base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")
ref_folder = os.path.join(base_path, "References")

for f in [input_folder, output_folder, voices_folder, ambience_folder, ref_folder]:
    os.makedirs(f, exist_ok=True)

# --- LİSTELEME FONKSİYONLARI ---
def sesleri_al():
    d = [f.split(".")[0] for f in os.listdir(voices_folder) if f.endswith(('.wav', '.mp3'))]
    return d if d else ["Ses Yok"]

def fonlari_al():
    d = [f.split(".")[0] for f in os.listdir(ambience_folder) if f.endswith(('.wav', '.mp3'))]
    return ["Yok"] + d

def referanslari_al():
    d = [f for f in os.listdir(ref_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    return d if d else ["Referans Yok"]

# --- YÜKLEME FONKSİYONLARI ---
def referans_yukle(files):
    if not files: return "Dosya seçilmedi."
    log = ""
    for file_obj in files:
        shutil.copy(file_obj.name, os.path.join(ref_folder, os.path.basename(file_obj.name)))
        log += f"✅ Yüklendi: {os.path.basename(file_obj.name)}\n"
    return log

# --- İŞLEM FONKSİYONLARI ---
def toplu_dosya_isle(files):
    if not files: return "Dosya seçilmedi."
    rapor = ""
    for file_obj in files:
        try:
            filename = os.path.basename(file_obj.name)
            with open(file_obj.name, "r", encoding="utf-8") as f: content = f.read()
            
            lines = content.split("\n")
            secilen_ses = "Ses Yok"
            secilen_fon = "Yok"
            baslangic = 0
            
            for i, line in enumerate(lines):
                if line.startswith("SES:"): secilen_ses = line.split(":")[1].strip()
                elif line.startswith("FON:"): secilen_fon = line.split(":")[1].strip()
                elif line.startswith("---"): baslangic = i + 1; break
            
            metin = "\n".join(lines[baslangic:])
            is_id = f"toplu_{filename}_{int(time.time())}"
            
            data = {"metin": metin, "ses": secilen_ses, "fon": secilen_fon}
            
            with open(os.path.join(input_folder, f"{is_id}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                
            rapor += f"✅ Kuyrukta: {filename}\n"
        except Exception as e:
            rapor += f"❌ Hata ({filename}): {str(e)}\n"
    return rapor

# --- ARAYÜZ TASARIMI ---
with gr.Blocks(title="AI MULTIMEDYA STUDIO") as demo:
    gr.Markdown("# 🎬 AI FİLM STÜDYOSU (V9.0 - TUTARLI KARAKTER MODU)")
    
    with gr.Tabs():
        # TAB 1: REFERANS YÖNETİMİ
        with gr.TabItem("🖼️ Referans Resim Yükle"):
            gr.Markdown("Hikayede kullanacağın karakter veya mekan resimlerini buraya yükle. İsimleri basit olsun (örn: `Ahmet.png`, `Ev.jpg`).")
            with gr.Row():
                ref_files = gr.File(file_count="multiple", label="Resimleri Sürükle")
                ref_btn = gr.Button("REFERANSLARI KAYDET", variant="secondary")
            ref_out = gr.Textbox(label="Durum")
            
            # Galeri (Mevcut resimleri göster)
            gr.Markdown("### 📂 Yüklü Referanslar")
            ref_gallery = gr.Gallery(label="Kayıtlı Resimler", columns=4, height=300)
            refresh_btn = gr.Button("Galeriyi Yenile")

            def galeri_guncelle():
                paths = [os.path.join(ref_folder, f) for f in os.listdir(ref_folder) if f.endswith(('.png','.jpg'))]
                return paths

            ref_btn.click(referans_yukle, ref_files, ref_out)
            refresh_btn.click(galeri_guncelle, outputs=ref_gallery)

        # TAB 2: İŞLEM MERKEZİ
        with gr.TabItem("📝 Senaryo İşle"):
            gr.Markdown("""
            **Nasıl Kullanılır?**
            Metnin içine `[REF: Ahmet.png]` yazarsan, o sahneyi Ahmet'e bakarak çizer.
            
            **Örnek Senaryo:**
            ```text
            SES: Ana_Florence
            FON: Savas_Muzigi
            ---
            [REF: Kral.png]
            [IMG: king sitting on throne, tired]
            Kral yorgun bir şekilde tahtında oturuyordu.

            [REF: Kral.png, Vezir.png]
            [IMG: king talking to advisor, angry]
            Vezir içeri girdiğinde kral ayağa kalktı.
            ```
            """)
            m_files = gr.File(file_count="multiple", label=".txt Senaryoları Yükle")
            m_btn = gr.Button("FİLMİ OLUŞTUR", variant="primary")
            m_out = gr.Textbox(label="Rapor", lines=5)
            
            m_btn.click(toplu_dosya_isle, m_files, m_out)

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True)