import os
import time
import json
import ollama

# --- AYARLAR ---
print("\n==================================================")
print(">>> YAZAR ROBOTU (V5.0 - AKILLI REJİ) <<<")
print("==================================================\n")

base_path = os.path.dirname(os.path.abspath(__file__))
input_folder = os.path.join(base_path, "Gelen_Isler")
os.makedirs(input_folder, exist_ok=True)

def ollama_sor(prompt):
    try:
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
        return response['message']['content']
    except: return ""

def seri_fikir_uret(tur, adet=6):
    print(f"🧠 '{tur}' için {adet} fikir düşünülüyor...")
    prompt = f"""
    Generate {adet} distinct story concepts for a YouTube channel about: '{tur}'.
    Return ONLY a Python list of strings. Example: ["Story 1", "Story 2"]
    """
    cevap = ollama_sor(prompt)
    try:
        start = cevap.find('[')
        end = cevap.rfind(']') + 1
        return json.loads(cevap[start:end])
    except:
        return [f"{tur} Story {i+1}" for i in range(adet)]

def uzun_hikaye_yaz(konu, kanal, dil="tr"):
    print(f"   ✍️ Yazılıyor ({kanal} Modu)...")
    tam_hikaye = ""
    
    # KANALA ÖZEL YÖNETMEN TALİMATLARI
    if kanal == "Uyku":
        # Uyku Modu: İlk 3 sahne görsel, gerisi siyah ekran
        visual_instruction = """
        - For the first 3 scenes: Use [IMG] tags with peaceful, dreamy descriptions.
        - For ALL remaining scenes: Use exactly [IMG: black screen].
        - Do NOT use [VID] tags.
        - Keep the tone very slow and hypnotic.
        """
    elif kanal == "Korku":
        # Korku Modu: Hibrit (Video + Resim + SFX)
        visual_instruction = """
        - Use a mix of [IMG] and [VID] tags.
        - Use [VID] for movement (shadows moving, doors opening).
        - Add [SFX] tags frequently (creaking, wind, heartbeat).
        - Atmosphere: Dark, scary, cinematic.
        """
    else: # Finans
        # Finans Modu: Hibrit (Basit Çizimler)
        visual_instruction = """
        - Use [IMG] for concepts (graphs, money bags).
        - Use [VID] rarely, only if simple movement fits.
        - Style: Minimalist stick figure.
        """

    bolumler = [
        "Introduction (300 words).",
        "Development (400 words).",
        "Deepening (400 words).",
        "Conclusion (300 words)."
    ]
    onceki = "Start."
    
    for b in bolumler:
        prompt = f"""
        Write a story part about: "{konu}". Lang: {dil}.
        Task: {b}
        Context: {onceki}
        
        DIRECTOR RULES: {visual_instruction}
        
        INSTRUCTIONS:
        - Write visual tags ([IMG], [VID], [SFX]) before paragraphs.
        - Write ONLY the story content.
        """
        yeni = ollama_sor(prompt)
        tam_hikaye += "\n" + yeni
        onceki = yeni[-500:]
    return tam_hikaye

def baslat():
    print("\n--- KANAL SEÇİMİ ---")
    print("1. Korku (Hibrit + SFX)")
    print("2. Uyku (Resim -> Siyah Ekran)")
    print("3. Finans (Hibrit Çöp Adam)")
    s = input("Seçim (1-3): ")
    
    if s=="1": tur="Horror Story"; k="Korku"; ses="Ana_Florence"; fon="Gerilim"; d="tr"
    elif s=="2": tur="Sleep Story"; k="Uyku"; ses="Ana_Florence"; fon="Yagmur"; d="tr"
    elif s=="3": tur="Finance Topic"; k="Finans"; ses="Ana_Florence"; fon="Yok"; d="tr"
    else: return

    # Dil Seçimi (Opsiyonel, varsayılan TR)
    print("\n--- DİL ---")
    print("1. Türkçe (Varsayılan)")
    print("2. İngilizce")
    l = input("Seçim: ")
    if l == "2": d = "en"

    seri_id = int(time.time())
    fikirler = seri_fikir_uret(tur, adet=6)
    
    for i, fikir in enumerate(fikirler):
        print(f"\n📚 BÖLÜM {i+1}/6: {fikir}")
        metin = uzun_hikaye_yaz(fikir, k, d)
        
        final = f"KANAL: {k}\nDIL: {d}\nSES: {ses}\nFON: {fon}\n---\n{metin}"
        fname = f"SERI_{seri_id}_PART_{i+1:02d}_{k}.json"
        
        with open(os.path.join(input_folder, fname), "w", encoding="utf-8") as f:
            json.dump({"metin": final, "ses": ses, "fon": fon}, f, ensure_ascii=False)
        
        print(f"📦 Gönderildi: {fname}")
        time.sleep(2)

    print(f"\n🎉 İŞ PLANI OLUŞTURULDU! Uyku modunda ekran kararacak, Korku modunda canlanacak.")

if __name__ == "__main__":
    baslat()