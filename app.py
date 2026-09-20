import streamlit as st
import pandas as pd
import json
import sqlite3
import base64
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage, ImageDraw, ImageFont
from datetime import datetime, timedelta

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

AUTO_BACKUP_FILE = "auto_backup.json"

# --- VERİTABANI VE OTOMATİK YEDEKLEME BAŞLANGIÇ İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect('adm_technics.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

def db_save(key, data):
    c = db_conn.cursor()
    c.execute("REPLACE INTO kv_store (key, value) VALUES (?, ?)", (key, json.dumps(data, ensure_ascii=False)))
    db_conn.commit()
    trigger_auto_backup()

def db_load(key, default_val):
    c = db_conn.cursor()
    c.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
    row = c.fetchone()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return default_val
    return default_val

def trigger_auto_backup():
    try:
        export_data = {
            "comp_name": st.session_state.get("comp_name", "ADM TECHNICS"),
            "comp_address": st.session_state.get("comp_address", "Scheepvaartstraat 5, Diepenbeek/België"),
            "comp_btw": st.session_state.get("comp_btw", "0707743276"),
            "comp_logo_b64": st.session_state.get("comp_logo_b64", None),
            "workers": st.session_state.get("workers", ["Adem", "Melih"]),
            "projects": st.session_state.get("projects", []),
            "expense_categories": st.session_state.get("expense_categories", []),
            "weekly_data": st.session_state.get("weekly_data", {}),
            "completed_weeks": list(st.session_state.get("completed_weeks", set())),
            "pdf_archive": st.session_state.get("pdf_archive", {})
        }
        with open(AUTO_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False)
    except Exception:
        pass

# --- UYGULAMA AÇILIRKEN OTOMATİK GERİ YÜKLEME KONTROLÜ ---
if os.path.exists(AUTO_BACKUP_FILE) and not db_load("weekly_data", {}):
    try:
        with open(AUTO_BACKUP_FILE, "r", encoding="utf-8") as f:
            imported_data = json.load(f)
            db_save("comp_name", imported_data.get("comp_name", "ADM TECHNICS"))
            db_save("comp_address", imported_data.get("comp_address", "Scheepvaartstraat 5, Diepenbeek/België"))
            db_save("comp_btw", imported_data.get("comp_btw", "0707743276"))
            db_save("comp_logo_b64", imported_data.get("comp_logo_b64", None))
            db_save("workers", imported_data.get("workers", ["Adem", "Melih"]))
            db_save("projects", imported_data.get("projects", []))
            db_save("expense_categories", imported_data.get("expense_categories", []))
            db_save("weekly_data", imported_data.get("weekly_data", {}))
            db_save("completed_weeks", imported_data.get("completed_weeks", []))
            db_save("pdf_archive", imported_data.get("pdf_archive", {}))
    except Exception:
        pass

st.markdown("""
    <style>
    .stTabs { margin-top: 15px !important; }
    div[data-baseweb="tab-list"] { gap: 4px; padding-top: 5px; }
    .block-container { padding-left: 0.5rem; padding-right: 0.5rem; padding-top: 0.8rem; max-width: 100%; }
    html, body, [class*="st-"] { font-size: 13px !important; }
    h1 { font-size: 1.3rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 1.0rem !important; }
    .streamlit-expanderHeader {
        border: 1px solid #1F4E78 !important;
        border-radius: 5px !important;
        background-color: #F8F9FA !important;
        margin-bottom: 4px;
        padding: 8px !important;
    }
    .table-container { width: 100%; overflow-x: auto; }
    .resp-table {
        width: 100% !important; border-collapse: collapse !important;
        font-size: 12px !important; margin: 6px 0 !important;
        background-color: white !important; color: #333 !important;
    }
    .resp-table th, .resp-table td { border: 1px solid #CBD5E1 !important; padding: 6px 4px !important; text-align: left !important; white-space: nowrap !important; }
    .resp-table th { background-color: #1F4E78 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# Session State & DB Senkronizasyonu
if 'comp_name' not in st.session_state:
    st.session_state.comp_name = db_load("comp_name", "ADM TECHNICS")
if 'comp_address' not in st.session_state:
    st.session_state.comp_address = db_load("comp_address", "Scheepvaartstraat 5, Diepenbeek/België")
if 'comp_btw' not in st.session_state:
    st.session_state.comp_btw = db_load("comp_btw", "0707743276")
if 'comp_logo_b64' not in st.session_state:
    st.session_state.comp_logo_b64 = db_load("comp_logo_b64", None)

def get_logo_io():
    if st.session_state.comp_logo_b64:
        try:
            img_bytes = base64.b64decode(st.session_state.comp_logo_b64)
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                bg = PILImage.new("RGB", pil_img.size, (255, 255, 255))
                if pil_img.mode == 'P':
                    pil_img = pil_img.convert('RGBA')
                bg.paste(pil_img, mask=pil_img.split()[3])
                pil_img = bg
            else:
                pil_img = pil_img.convert("RGB")
            
            out_io = io.BytesIO()
            pil_img.save(out_io, format='JPEG', quality=95)
            out_io.seek(0)
            return out_io
        except Exception:
            return None
    return None

if 'workers' not in st.session_state:
    st.session_state.workers = db_load("workers", ["Adem", "Melih"])

if 'projects' not in st.session_state:
    st.session_state.projects = db_load("projects", [
        {"name": "Kruidvat Diepenbeek", "code": "E260001"},
        {"name": "ICI PARIS XL Hasselt", "code": "E260002"},
        {"name": "Kruidvat Brakel", "code": "E260246"}
    ])

if 'expense_categories' not in st.session_state:
    st.session_state.expense_categories = db_load("expense_categories", ["Malzeme", "Su borusu", "Şalter", "Parking", "Kabel", "Verlichting"])

if 'weekly_data' not in st.session_state:
    st.session_state.weekly_data = db_load("weekly_data", {})
if 'completed_weeks' not in st.session_state:
    st.session_state.completed_weeks = set(db_load("completed_weeks", []))
if 'pdf_archive' not in st.session_state:
    st.session_state.pdf_archive = db_load("pdf_archive", {})

day_to_nl = {
    "Pazartesi": "Maandag",
    "Salı": "Dinsdag",
    "Çarşamba": "Woensdag",
    "Perşembe": "Donderdag",
    "Cuma": "Vrijdag",
    "Cumartesi": "Zaterdag",
    "Zondag": "Zondag"
}

def get_date_for_day(year, week, day_idx):
    try:
        dt = datetime.fromisocalendar(year, week, day_idx + 1)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return ""

def generate_slots(start_h, start_m, end_h, end_m):
    slots = []
    curr = datetime(2026, 1, 1, start_h, start_m)
    end = datetime(2026, 1, 1, end_h, end_m)
    while curr <= end:
        slots.append(curr.strftime("%H:%M"))
        curr += timedelta(minutes=15)
    return slots

start_slots = generate_slots(3, 30, 10, 30)
end_slots = generate_slots(12, 30, 19, 30)
pause_slots = ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45", "02:00"]

def calculate_net_hours(start_str, pause_str, end_str):
    try:
        t_start = datetime.strptime(start_str, "%H:%M")
        t_pause = datetime.strptime(pause_str, "%H:%M")
        t_end = datetime.strptime(end_str, "%H:%M")
        duration = t_end - t_start
        pause_duration = timedelta(hours=t_pause.hour, minutes=t_pause.minute)
        net_duration = duration - pause_duration
        total_hours = net_duration.total_seconds() / 3600
        return max(0.0, round(total_hours, 2))
    except Exception:
        return 0.0

# Sekmeler
tab_entry, tab_preview, tab_projects, tab_archive, tab_settings = st.tabs([
    "📝 Werkbon", "📊 Özet", "📁 Projeler", "📚 Arşiv", "⚙️ Ayarlar"
])

with tab_settings:
    st.header("⚙️ Ayarlar ve Otomatik Güvenlik")
    
    st.subheader("Firma Bilgileri")
    logo_io = get_logo_io()
    if logo_io is not None:
        st.image(logo_io, width=70, caption="Mevcut Logo")
        
    uploaded_logo = st.file_uploader("Logo Değiştir (PNG / JPG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        try:
            b64_str = base64.b64encode(uploaded_logo.getvalue()).decode('utf-8')
            st.session_state.comp_logo_b64 = b64_str
            db_save("comp_logo_b64", b64_str)
            st.success("Logo güncellendi!")
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

    new_comp_name = st.text_input("Firma Adı", value=st.session_state.comp_name)
    if new_comp_name != st.session_state.comp_name:
        st.session_state.comp_name = new_comp_name
        db_save("comp_name", new_comp_name)

    new_comp_address = st.text_input("Firma Adresi", value=st.session_state.comp_address)
    if new_comp_address != st.session_state.comp_address:
        st.session_state.comp_address = new_comp_address
        db_save("comp_address", new_comp_address)

    new_comp_btw = st.text_input("BTW Numarası", value=st.session_state.comp_btw)
    if new_comp_btw != st.session_state.comp_btw:
        st.session_state.comp_btw = new_comp_btw
        db_save("comp_btw", new_comp_btw)

    st.markdown("---")
    st.subheader("Çalışanlar")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        new_w = st.text_input("Yeni Çalışan Adı", label_visibility="collapsed")
    with col_w2:
        if st.button("Çalışan Ekle"):
            if new_w and new_w not in st.session_state.workers:
                st.session_state.workers.append(new_w)
                db_save("workers", st.session_state.workers)
                st.rerun()
    for w in st.session_state.workers:
        cw = st.columns([3, 1])
        cw[0].write(f"- {w}")
        if len(st.session_state.workers) > 1 and cw[1].button("Sil", key=f"del_w_{w}"):
            st.session_state.workers.remove(w)
            db_save("workers", st.session_state.workers)
            st.rerun()

    st.markdown("---")
    st.subheader("Gider / Malzeme Kategorileri")
    col_ex1, col_ex2 = st.columns([2, 1])
    with col_ex1:
        new_exp_cat = st.text_input("Yeni Gider/Malzeme Türü", label_visibility="collapsed")
    with col_ex2:
        if st.button("Kategori Ekle"):
            if new_exp_cat and new_exp_cat not in st.session_state.expense_categories:
                st.session_state.expense_categories.append(new_exp_cat)
                db_save("expense_categories", st.session_state.expense_categories)
                st.rerun()
    for cat in st.session_state.expense_categories:
        cc = st.columns([3, 1])
        cc[0].write(f"- {cat}")
        if len(st.session_state.expense_categories) > 1 and cc[1].button("Sil", key=f"del_cat_{cat}"):
            st.session_state.expense_categories.remove(cat)
            db_save("expense_categories", st.session_state.expense_categories)
            st.rerun()

    st.markdown("---")
    st.subheader("💾 Veri Yedekleme ve Excel Raporu")
    
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            all_flat_entries = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for entry in wk_val.get("entries", []):
                    all_flat_entries.append({"Hafta": wk_k, **entry})
            if all_flat_entries:
                pd.DataFrame(all_flat_entries).to_excel(writer, sheet_name='Calisma_Kayitlari', index=False)
            
            all_flat_expenses = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for exp in wk_val.get("expenses", []):
                    exp_copy = exp.copy()
                    exp_copy.pop("Görsel_b64", None)
                    all_flat_expenses.append({"Hafta": wk_k, **exp_copy})
            if all_flat_expenses:
                pd.DataFrame(all_flat_expenses).to_excel(writer, sheet_name='Giderler_Fisler', index=False)
                
            if st.session_state.projects:
                pd.DataFrame(st.session_state.projects).to_excel(writer, sheet_name='Projeler', index=False)
                
            if st.session_state.workers:
                pd.DataFrame({"Calisanlar": st.session_state.workers}).to_excel(writer, sheet_name='Calisanlar', index=False)
        excel_data = excel_buffer.getvalue()
        
        st.download_button(
            label="📊 Tüm Verileri Excel Olarak İndir (.xlsx)",
            data=excel_data,
            file_name=f"adm_technics_rapor_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception:
        pass

    export_data = {
        "comp_name": st.session_state.comp_name,
        "comp_address": st.session_state.comp_address,
        "comp_btw": st.session_state.comp_btw,
        "workers": st.session_state.workers,
        "projects": st.session_state.projects,
        "expense_categories": st.session_state.expense_categories,
        "weekly_data": st.session_state.weekly_data,
        "completed_weeks": list(st.session_state.completed_weeks)
    }
    json_str = json.dumps(export_data, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Tüm Verileri Yedekle (JSON)",
        data=json_str,
        file_name=f"adm_technics_yedek_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

    uploaded_backup = st.file_uploader("📂 Yedek Geri Yükle", type=["json"])
    if uploaded_backup is not None:
        try:
            imported_data = json.load(uploaded_backup)
            st.session_state.comp_name = imported_data.get("comp_name", st.session_state.comp_name)
            st.session_state.comp_address = imported_data.get("comp_address", st.session_state.comp_address)
            st.session_state.comp_btw = imported_data.get("comp_btw", st.session_state.comp_btw)
            st.session_state.workers = imported_data.get("workers", st.session_state.workers)
            st.session_state.projects = imported_data.get("projects", st.session_state.projects)
            st.session_state.expense_categories = imported_data.get("expense_categories", st.session_state.expense_categories)
            st.session_state.weekly_data = imported_data.get("weekly_data", {})
            st.session_state.completed_weeks = set(imported_data.get("completed_weeks", []))
            
            db_save("comp_name", st.session_state.comp_name)
            db_save("comp_address", st.session_state.comp_address)
            db_save("comp_btw", st.session_state.comp_btw)
            db_save("workers", st.session_state.workers)
            db_save("projects", st.session_state.projects)
            db_save("expense_categories", st.session_state.expense_categories)
            db_save("weekly_data", st.session_state.weekly_data)
            db_save("completed_weeks", list(st.session_state.completed_weeks))
            st.success("Geri yüklendi!")
            st.rerun()
        except Exception as e:
            st.error(f"Hata: {e}")

with tab_projects:
    st.header("📁 Proje Yönetimi ve Geçmiş Kayıtlar")
    with st.form("add_project_form"):
        p_name = st.text_input("Proje / Müşteri Adı")
        p_code = st.text_input("Proje Numarası / Kodu (Örn: E260003)")
        if st.form_submit_button("Proje Kaydet") and p_name:
            st.session_state.projects.append({"name": p_name, "code": p_code if p_code else "E260000"})
            db_save("projects", st.session_state.projects)
            st.success("Proje eklendi!")
            st.rerun()
            
    for idx, prj in enumerate(st.session_state.projects):
        with st.expander(f"📌 {prj['code']} - {prj['name']}"):
            upd_name = st.text_input("Ad", value=prj['name'], key=f"upd_n_{idx}")
            upd_code = st.text_input("Kod", value=prj['code'], key=f"upd_c_{idx}")
            
            pcol1, pcol2 = st.columns([1, 1])
            with pcol1:
                if st.button("Güncelle", key=f"up_p_{idx}"):
                    prj['name'] = upd_name
                    prj['code'] = upd_code
                    db_save("projects", st.session_state.projects)
                    st.success("Güncellendi!")
                    st.rerun()
            with pcol2:
                if st.button("🗑️ Projeyi Sil", key=f"del_p_{idx}"):
                    st.session_state.projects.pop(idx)
                    db_save("projects", st.session_state.projects)
                    st.success("Proje silindi!")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("#### 📋 Projeye Ait Geçmiş Kayıtlar")
            proj_full_name = f"{prj['code']} - {prj['name']}"
            matched_entries = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for entry in wk_val.get("entries", []):
                    if entry.get("Proje") == proj_full_name or prj['name'] in entry.get("Proje", "") or prj['code'] in entry.get("Proje", ""):
                        matched_entries.append({**entry, "Hafta": wk_k})
            
            if matched_entries:
                df_proj = pd.DataFrame(matched_entries)
                st.markdown(f'<div class="table-container">{df_proj[["Hafta", "Gün", "Tarih", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            else:
                st.info("Bu projeye ait henüz kayıt bulunmuyor.")

with tab_archive:
    st.header("📚 PDF Arşivi")
    if st.session_state.pdf_archive:
        for filename, b64_pdf in list(st.session_state.pdf_archive.items()):
            col_ar1, col_ar2, col_ar3 = st.columns([3, 1, 1])
            with col_ar1:
                st.write(f"📄 {filename}")
            with col_ar2:
                try:
                    st.download_button("📥 İndir", data=base64.b64decode(b64_pdf), file_name=filename, mime="application/pdf", key=f"arch_dl_{filename}")
                except Exception:
                    pass
            with col_ar3:
                if st.button("🗑️ Sil", key=f"arch_del_{filename}"):
                    del st.session_state.pdf_archive[filename]
                    db_save("pdf_archive", st.session_state.pdf_archive)
                    st.rerun()
    else:
        st.info("Arşiv boş.")

today = datetime.today()
current_iso_year, current_iso_week, _ = today.isocalendar()

with tab_preview:
    st.header("📊 Haftalık Özet ve Detaylı Analiz")
    
    col_py1, col_py2 = st.columns(2)
    with col_py1:
        prev_sel_year = st.slider("Yıl", 2026, 2035, current_iso_year, key="prev_y_slide")
    with col_py2:
        prev_week_no = st.slider("Hafta No", 1, 53, current_iso_week, key="prev_w_slide")
        
    wk_key = f"{prev_sel_year}-W{prev_week_no}"
    w_data = st.session_state.weekly_data.get(wk_key, {"entries": [], "expenses": []})
    
    if w_data["entries"]:
        df_p = pd.DataFrame(w_data["entries"])
        
        st.markdown("### 📋 Tüm Çalışma Kayıtları")
        st.markdown(f'<div class="table-container">{df_p[["Gün", "Tarih", "Proje", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        col_sum1, col_sum2 = st.columns(2)
        
        with col_sum1:
            st.markdown("#### 👷 Çalışan Bazlı Toplam Saatler")
            df_worker = df_p.groupby("Çalışan")["Saat"].sum().reset_index()
            st.markdown(f'<div class="table-container">{df_worker.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            
        with col_sum2:
            st.markdown("#### 📁 Proje Bazlı Toplam Saatler")
            df_proj_sum = df_p.groupby("Proje")["Saat"].sum().reset_index()
            st.markdown(f'<div class="table-container">{df_proj_sum.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
    else:
        st.info("Bu hafta için henüz kayıt bulunmuyor.")
```Haklısın, kusura bakma; istediğin son eklemeleri ve değişiklikleri bu koda entegre etmek yerine gözden kaçırmışım. 

Yapmak istediğin o son istekleri (özellikleri, alanları veya düzeltmeleri) kısaca hatırlatırsan, hemen bu kodun içine eksiksiz bir şekilde entegre edip güncel ve çalışır halini sana sunayım. Neydi eklemek/değiştirmek istediğin detaylar, yazman yeterli!
