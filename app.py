import streamlit as st
import psycopg2
import json
import base64
import zipfile
import io
import os

# Supabase Bağlantı Bilgilerini Buraya Gir
# (Eski kodundaki bağlantı cümlesini buraya yapıştır)
DB_URL = "postgresql://postgres.iowaxfgqfehdentzyipq:SIFRENIZ@aws-1-eu-west-1.pooler.supabase.co:5432/postgres"

st.title("🚀 Veri Dönüştürücü (Android'e Geçiş)")
st.write("Bu butona basarak eski verilerinizi Android uygulamasının okuyabileceği formata çevirebilirsiniz.")

if st.button("Verileri Çek ve Dönüştür"):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM kv_store")
        rows = cur.fetchall()
        
        # Android'in Beklediği Temel Dosyalar
        data_dict = {}
        weeks_dict = {}
        expenses_dict = {}
        
        # Resimler için klasör
        os.makedirs("receipts", exist_ok=True)
        receipt_counter = 1
        
        for key, val_str in rows:
            try:
                val = json.loads(val_str)
            except:
                val = val_str
                
            if key == "weekly_data":
                for week_key, week_data in val.items():
                    entries = []
                    for e in week_data.get("entries", []):
                        # Tarihi ve dakikayı Android formatına çevir
                        day_str = e.get("Gün", "Pazartesi")
                        day_map = {"Pazartesi": 0, "Salı": 1, "Çarşamba": 2, "Perşembe": 3, "Cuma": 4}
                        day_int = day_map.get(day_str, 0)
                        
                        def time_to_min(t_str):
                            try:
                                h, m = map(int, t_str.split(":"))
                                return h * 60 + m
                            except: return 0
                            
                        entries.append({
                            "day": day_int,
                            "project": e.get("Proje", ""),
                            "worker": e.get("Çalışan", ""),
                            "start": time_to_min(e.get("Başlangıç", "00:00")),
                            "pause": time_to_min(e.get("Mola", "00:00")),
                            "end": time_to_min(e.get("Bitiş", "00:00"))
                        })
                    weeks_dict[week_key] = entries
                    
                    # Fişleri İşle
                    exp_list = []
                    for ex in week_data.get("expenses", []):
                        img_b64 = ex.get("Görsel_b64", "")
                        img_name = ""
                        
                        # Eğer fişte resim varsa, base64'ü ayır ve dosyaya kaydet
                        if img_b64:
                            try:
                                img_name = f"receipt_{receipt_counter}.jpg"
                                with open(f"receipts/{img_name}", "wb") as f:
                                    f.write(base64.b64decode(img_b64))
                                receipt_counter += 1
                            except Exception as img_err:
                                img_name = ""
                        
                        exp_list.append({
                            "id": str(receipt_counter),
                            "day": day_map.get(ex.get("Gün", "Pazartesi"), 0),
                            "project": ex.get("Proje", ""),
                            "category": ex.get("Açıklama", "Diğer"),
                            "amount": float(ex.get("Tutar", 0.0)),
                            "image": img_name
                        })
                    expenses_dict[week_key] = exp_list
                    
            elif key == "workers":
                # Ayarları kaydet
                data_dict["workers"] = [{"name": w, "rate": 25.0} for w in val]
            elif key == "projects":
                data_dict["projects"] = [{"code": p["code"], "name": p["name"], "customerName": ""} for p in val]
            elif key == "comp_name":
                data_dict["compName"] = val
            elif key == "comp_address":
                data_dict["compAddress"] = val
            elif key == "comp_email":
                data_dict["compEmail"] = val
            elif key == "comp_gsm":
                data_dict["compGsm"] = val
            elif key == "comp_btw":
                data_dict["compBtw"] = val
                
        # JSON dosyalarını oluştur
        with open("werkbon_data.json", "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False)
        with open("werkbon_weeks.json", "w", encoding="utf-8") as f:
            json.dump(weeks_dict, f, ensure_ascii=False)
        with open("werkbon_expenses.json", "w", encoding="utf-8") as f:
            json.dump(expenses_dict, f, ensure_ascii=False)
            
        # Hepsini tek bir ZIP dosyasına koy
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.write("werkbon_data.json")
            zf.write("werkbon_weeks.json")
            zf.write("werkbon_expenses.json")
            for root, dirs, files in os.walk("receipts"):
                for file in files:
                    zf.write(os.path.join(root, file), f"receipts/{file}")
                    
        st.success("Dönüşüm Başarılı! Aşağıdaki butondan ZIP dosyasını indirin.")
        st.download_button(
            label="📥 ZIP Olarak İndir",
            data=zip_buffer.getvalue(),
            file_name="Werkbon_Eski_Yedek.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
