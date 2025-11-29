import gradio as gr
import os
import json
import time
import shutil

# --- DÜZELTİLMİŞ AYARLAR ---
# Dosyanın bulunduğu klasörü (Projects) baz al
base_path = os.path.dirname(os.path.abspath(__file__))

input_folder = os.path.join(base_path, "Gelen_Isler")
output_folder = os.path.join(base_path, "Tamamlananlar")
voices_folder = os.path.join(base_path, "Voices")
ambience_folder = os.path.join(base_path, "Ambience")

os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)
os.makedirs(voices_folder, exist_ok=True)
os.makedirs(ambience_folder, exist_ok=True)
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)
os.makedirs(voices_folder, exist_ok=True)
os.makedirs(ambience_folder, exist_ok=True)

def sesleri_al():
    d = [f.split(".")[0] for f in os.listdir(voices_folder) if f.endswith(('.wav', '.mp3'))]
    return d if d else ["Ses Yok"]

def fonlari_al():
    d = [f.split(".")[0] for f in os.listdir(ambience_folder) if f.endswith(('.wav', '.mp3'))]
    return ["Yok"] + d

# --- FONKSİYONLAR ---

def tekli_is_ver(metin, ses_adi, fon_adi):
    if not metin or ses_adi == "Ses Yok": return "Eksik bilgi!"
    
    is_id = f"tek_{int(time.time())}"
    json_path = os.path.join(input_folder, f"{is_id}.json")
    
    data = {"metin": metin, "ses": ses_adi, "fon": fon_adi}
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    
    return f"Sipariş verildi! ID: {is_id} (Tamamlananlar klasörünü bekle)"

def toplu_dosya_isle(files):
    if not files: return "Dosya seçilmedi."
    
    rapor = ""
    for file_obj in files:
        try:
            # Dosya içeriğini oku
            filename = os.path.basename(file_obj.name)
            with open(file_obj.name, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Formatı Ayrıştır (SES: X, FON: Y, --- Metin)
            lines = content.split("\n")
            
            secilen_ses = "Ses Yok"
            secilen_fon = "Yok"
            baslangic_satiri = 0
            
            # Başlıkları Oku
            for i, line in enumerate(lines):
                if line.startswith("SES:"):
                    secilen_ses = line.split(":")[1].strip()
                elif line.startswith("FON:"):
                    secilen_fon = line.split(":")[1].strip()
                elif line.startswith("---"):
                    baslangic_satiri = i + 1
                    break
            
            # Eğer etiket yoksa varsayılanları kullanır, metnin tamamını alır
            metin = "\n".join(lines[baslangic_satiri:])
            
            # İşi Oluştur
            is_id = f"toplu_{filename}_{int(time.time())}"
            json_path = os.path.join(input_folder, f"{is_id}.json")
            
            data = {"metin": metin, "ses": secilen_ses, "fon": secilen_fon}
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                
            rapor += f"✅ {filename} -> Kuyruğa Eklendi (Ses: {secilen_ses}, Fon: {secilen_fon})\n"
            
        except Exception as e:
            rapor += f"❌ {filename} -> HATA: {str(e)}\n"
            
    return rapor

# --- ARAYÜZ ---
with gr.Blocks(title="AI STÜDYO PRO") as demo:
    gr.Markdown("## 🎙️ YOUTUBE OTOMASYON STÜDYOSU")
    
    with gr.Tabs():
        # TAB 1: TEKİL İŞLEM (Hızlı Test)
        with gr.TabItem("Tekli Üretim"):
            with gr.Row():
                with gr.Column():
                    t_txt = gr.Textbox(label="Metin", lines=5)
                    t_ses = gr.Dropdown(label="Ses Seç", choices=sesleri_al())
                    t_fon = gr.Dropdown(label="Fon Müziği Seç", choices=fonlari_al())
                    t_btn = gr.Button("BAŞLAT", variant="primary")
                with gr.Column():
                    t_out = gr.Label(label="Durum")
            
            t_btn.click(tekli_is_ver, [t_txt, t_ses, t_fon], t_out)

        # TAB 2: TOPLU İŞLEM (Dosya Yükleme)
        with gr.TabItem("Toplu Dosya İşleme (.txt)"):
            gr.Markdown("""
            **Format:** Dosyanın başına şunları ekleyin:
            ```text
            SES: İlber_Ortayli
            FON: Savas_Muzigi
            ---
            Hikaye buraya...
            ```
            """)
            m_files = gr.File(file_count="multiple", label=".txt Dosyalarını Buraya Sürükle")
            m_btn = gr.Button("DOSYALARI İŞLE", variant="primary")
            m_out = gr.Textbox(label="İşlem Raporu", lines=10)
            
            m_btn.click(toplu_dosya_isle, m_files, m_out)

        # TAB 3: KÜTÜPHANE
        with gr.TabItem("Kütüphane Yönetimi"):
            gr.Markdown("Sesleri ve Müzikleri `Projects/Voices` ve `Projects/Ambience` klasörlerine atabilirsiniz. Listeyi yenilemek için sayfayı yenileyin.")

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True)