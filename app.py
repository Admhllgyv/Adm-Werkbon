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

# --- VERİTABANI VE OTOMATİK YEDEKLEME İŞLEMLERİ ---
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
            "comp_email": st.session_state.get("comp_email", "admtechnics2018@gmail.com"),
            "comp_gsm": st.session_state.get("comp_gsm", "0467752557"),
            "comp_btw": st.session_state.get("comp_btw", "0707743276"),
            "comp_logo_b64": st.session_state.get("comp_logo_b64", None),
            "workers": st.session_state.get("workers", ["Adem", "Melih"]),
            "worker_rates": st.session_state.get("worker_rates", {"Adem": 25.0, "Melih": 20.0}),
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

# --- UYGULAMA AÇILIRKEN GERİ YÜKLEME ---
if os.path.exists(AUTO_BACKUP_FILE) and not db_load("weekly_data", {}):
    try:
        with open(AUTO_BACKUP_FILE, "r", encoding="utf-8") as f:
            imported_data = json.load(f)
            db_save("comp_name", imported_data.get("comp_name", "ADM TECHNICS"))
            db_save("comp_address", imported_data.get("comp_address", "Scheepvaartstraat 5, Diepenbeek/België"))
            db_save("comp_email", imported_data.get("comp_email", "admtechnics2018@gmail.com"))
            db_save("comp_gsm", imported_data.get("comp_gsm", "0467752557"))
            db_save("comp_btw", imported_data.get("comp_btw", "0707743276"))
            db_save("comp_logo_b64", imported_data.get("comp_logo_b64", None))
            db_save("workers", imported_data.get("workers", ["Adem", "Melih"]))
            db_save("worker_rates", imported_data.get("worker_rates", {"Adem": 25.0, "Melih": 20.0}))
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

# Session State Senkronizasyonu
if 'comp_name' not in st.session_state:
    st.session_state.comp_name = db_load("comp_name", "ADM TECHNICS")
if 'comp_address' not in st.session_state:
    st.session_state.comp_address = db_load("comp_address", "Scheepvaartstraat 5, Diepenbeek/België")
if 'comp_email' not in st.session_state:
    st.session_state.comp_email = db_load("comp_email", "admtechnics2018@gmail.com")
if 'comp_gsm' not in st.session_state:
    st.session_state.comp_gsm = db_load("comp_gsm", "0467752557")
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

if 'worker_rates' not in st.session_state:
    st.session_state.worker_rates = db_load("worker_rates", {"Adem": 25.0, "Melih": 20.0})

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

start_slots = generate_slots(3, 0, 22, 0)
end_slots = generate_slots(3, 0, 22, 0)
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
tab_entry, tab_preview, tab_monthly, tab_projects, tab_archive, tab_settings = st.tabs([
    "📝 Werkbon", "📊 Özet", "📅 Aylık Rapor", "📁 Projeler", "📚 Arşiv", "⚙️ Ayarlar"
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

    new_comp_email = st.text_input("E-posta Adresi", value=st.session_state.comp_email)
    if new_comp_email != st.session_state.comp_email:
        st.session_state.comp_email = new_comp_email
        db_save("comp_email", new_comp_email)

    new_comp_gsm = st.text_input("GSM Numarası", value=st.session_state.comp_gsm)
    if new_comp_gsm != st.session_state.comp_gsm:
        st.session_state.comp_gsm = new_comp_gsm
        db_save("comp_gsm", new_comp_gsm)

    new_comp_btw = st.text_input("BTW Numarası", value=st.session_state.comp_btw)
    if new_comp_btw != st.session_state.comp_btw:
        st.session_state.comp_btw = new_comp_btw
        db_save("comp_btw", new_comp_btw)

    st.markdown("---")
    st.subheader("Çalışanlar ve Saatlik Ücretler (€)")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        new_w = st.text_input("Yeni Çalışan Adı", label_visibility="collapsed")
    with col_w2:
        if st.button("Çalışan Ekle"):
            if new_w and new_w not in st.session_state.workers:
                st.session_state.workers.append(new_w)
                if new_w not in st.session_state.worker_rates:
                    st.session_state.worker_rates[new_w] = 20.0
                db_save("workers", st.session_state.workers)
                db_save("worker_rates", st.session_state.worker_rates)
                st.rerun()

    for w in st.session_state.workers:
        cw = st.columns([2, 2, 1])
        cw[0].write(f"👷 **{w}**")
        current_rate = float(st.session_state.worker_rates.get(w, 20.0))
        new_rate = cw[1].number_input(f"Saatlik Ücret (€) - {w}", min_value=0.0, value=current_rate, step=1.0, key=f"rate_set_{w}", label_visibility="collapsed")
        if new_rate != current_rate:
            st.session_state.worker_rates[w] = new_rate
            db_save("worker_rates", st.session_state.worker_rates)
        
        if len(st.session_state.workers) > 1 and cw[2].button("Sil", key=f"del_w_{w}"):
            st.session_state.workers.remove(w)
            if w in st.session_state.worker_rates:
                del st.session_state.worker_rates[w]
            db_save("workers", st.session_state.workers)
            db_save("worker_rates", st.session_state.worker_rates)
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
                pd.DataFrame({"Calisanlar": st.session_state.workers, "Saatlik_Ucret": [st.session_state.worker_rates.get(w, 20.0) for w in st.session_state.workers]}).to_excel(writer, sheet_name='Calisanlar', index=False)
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
        "comp_email": st.session_state.comp_email,
        "comp_gsm": st.session_state.comp_gsm,
        "comp_btw": st.session_state.comp_btw,
        "comp_logo_b64": st.session_state.comp_logo_b64,
        "workers": st.session_state.workers,
        "worker_rates": st.session_state.worker_rates,
        "projects": st.session_state.projects,
        "expense_categories": st.session_state.expense_categories,
        "weekly_data": st.session_state.weekly_data,
        "completed_weeks": list(st.session_state.completed_weeks),
        "pdf_archive": st.session_state.pdf_archive
    }
    json_str = json.dumps(export_data, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Tüm Verileri Eksiksiz Yedekle (JSON)",
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
            st.session_state.comp_email = imported_data.get("comp_email", st.session_state.comp_email)
            st.session_state.comp_gsm = imported_data.get("comp_gsm", st.session_state.comp_gsm)
            st.session_state.comp_btw = imported_data.get("comp_btw", st.session_state.comp_btw)
            st.session_state.comp_logo_b64 = imported_data.get("comp_logo_b64", st.session_state.comp_logo_b64)
            st.session_state.workers = imported_data.get("workers", st.session_state.workers)
            st.session_state.worker_rates = imported_data.get("worker_rates", st.session_state.worker_rates)
            st.session_state.projects = imported_data.get("projects", [])
            st.session_state.expense_categories = imported_data.get("expense_categories", st.session_state.expense_categories)
            st.session_state.weekly_data = imported_data.get("weekly_data", {})
            st.session_state.completed_weeks = set(imported_data.get("completed_weeks", []))
            st.session_state.pdf_archive = imported_data.get("pdf_archive", {})
            
            db_save("comp_name", st.session_state.comp_name)
            db_save("comp_address", st.session_state.comp_address)
            db_save("comp_email", st.session_state.comp_email)
            db_save("comp_gsm", st.session_state.comp_gsm)
            db_save("comp_btw", st.session_state.comp_btw)
            db_save("comp_logo_b64", st.session_state.comp_logo_b64)
            db_save("workers", st.session_state.workers)
            db_save("worker_rates", st.session_state.worker_rates)
            db_save("projects", st.session_state.projects)
            db_save("expense_categories", st.session_state.expense_categories)
            db_save("weekly_data", st.session_state.weekly_data)
            db_save("completed_weeks", list(st.session_state.completed_weeks))
            db_save("pdf_archive", st.session_state.pdf_archive)
            st.success("Tüm veriler eksiksiz geri yüklendi!")
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
    st.header("📚 PDF Arşivi ve Önizleme")
    st.caption("Arşivdeki PDF'leri tarayıcınızda açmak veya indirmek için butonları kullanabilirsiniz.")
    if st.session_state.pdf_archive:
        for filename, b64_pdf in list(st.session_state.pdf_archive.items()):
            col_ar1, col_ar2, col_ar3 = st.columns([2, 1, 1])
            with col_ar1:
                st.write(f"📄 {filename}")
            with col_ar2:
                try:
                    pdf_bytes = base64.b64decode(b64_pdf)
                    st.download_button("📥 İndir", data=pdf_bytes, file_name=filename, mime="application/pdf", key=f"arch_dl_{filename}")
                except Exception:
                    pass
            with col_ar3:
                pdf_data_url = f"data:application/pdf;base64,{b64_pdf}"
                st.markdown(f'<a href="{pdf_data_url}" target="_blank" style="display:inline-block;padding:0.4rem 0.8rem;background-color:#2563EB;color:white;text-decoration:none;border-radius:4px;font-size:12px;font-weight:bold;text-align:center;">🔍 Önizle</a>', unsafe_allow_html=True)
            
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
            
        st.markdown("---")
        st.markdown("#### 🔍 Proje & Çalışan Detay Matrisi")
        df_pivot = df_p.pivot_table(index="Proje", columns="Çalışan", values="Saat", aggfunc="sum", fill_value=0).reset_index()
        st.markdown(f'<div class="table-container">{df_pivot.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
        
    else:
        st.info("Bu hafta için henüz kayıt bulunmuyor.")

with tab_monthly:
    st.header("📅 Aylık Rapor ve Anlık Saatlik Ücret Yönetimi")
    
    col_my1, col_my2, col_my3 = st.columns(3)
    with col_my1:
        sel_month_year = st.selectbox("Yıl Seçimi", [2026, 2027, 2028, 2029, 2030], index=0, key="monthly_year_sel")
    with col_my2:
        month_options = {
            "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
            "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12
        }
        sel_month_name = st.selectbox("Ay Seçimi", list(month_options.keys()), index=today.month - 1, key="monthly_name_sel")
        sel_month_no = month_options[sel_month_name]
    with col_my3:
        worker_filter_options = ["Tümü"] + st.session_state.workers
        sel_worker_filter = st.selectbox("Çalışan Filtresi", worker_filter_options, key="monthly_worker_filter")

    st.markdown("---")
    st.markdown("### ⚙️ Çalışan Saatlik Ücretleri (Anlık Düzenle)")
    rate_cols = st.columns(len(st.session_state.workers) if st.session_state.workers else 1)
    for i, w in enumerate(st.session_state.workers):
        col_idx = i % len(rate_cols)
        with rate_cols[col_idx]:
            curr_r = float(st.session_state.worker_rates.get(w, 20.0))
            new_r = st.number_input(f"{w} (€/saat)", min_value=0.0, value=curr_r, step=1.0, key=f"monthly_rate_input_{w}")
            if new_r != curr_r:
                st.session_state.worker_rates[w] = new_r
                db_save("worker_rates", st.session_state.worker_rates)

    monthly_entries = []
    monthly_expenses = []

    for wk_k, wk_val in st.session_state.weekly_data.items():
        for entry in wk_val.get("entries", []):
            tarih_str = entry.get("Tarih", "")
            try:
                dt = datetime.strptime(tarih_str, "%d.%m.%Y")
                if dt.year == sel_month_year and dt.month == sel_month_no:
                    if sel_worker_filter == "Tümü" or entry.get("Çalışan") == sel_worker_filter:
                        monthly_entries.append(entry)
            except Exception:
                pass
                
        for exp in wk_val.get("expenses", []):
            tarih_str = exp.get("Tarih", "")
            try:
                dt = datetime.strptime(tarih_str, "%d.%m.%Y")
                if dt.year == sel_month_year and dt.month == sel_month_no:
                    monthly_expenses.append(exp)
            except Exception:
                pass

    if monthly_entries:
        df_m = pd.DataFrame(monthly_entries)
        total_m_hours = df_m["Saat"].sum()
        total_m_cost = sum([ex.get("Tutar", 0) for ex in monthly_expenses])
        
        st.markdown("---")
        st.markdown("### 💶 Çalışan Bazlı Aylık Kazanç Hesaplama")
        
        worker_hours_dict = df_m.groupby("Çalışan")["Saat"].sum().to_dict()
        
        calc_rows = []
        total_earnings_calc = 0.0
        for w in st.session_state.workers:
            if sel_worker_filter == "Tümü" or sel_worker_filter == w:
                hrs = worker_hours_dict.get(w, 0.0)
                rate = float(st.session_state.worker_rates.get(w, 20.0))
                earnings = hrs * rate
                total_earnings_calc += earnings
                calc_rows.append({
                    "Çalışan": w,
                    "Toplam Saat": hrs,
                    "Saatlik Ücret (€)": rate,
                    "Toplam Kazanç (€)": round(earnings, 2)
                })
        
        if calc_rows:
            df_calc = pd.DataFrame(calc_rows)
            st.markdown(f'<div class="table-container">{df_calc.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            st.markdown(f"**Seçilen Dönem Toplam İşçi Maliyeti / Kazancı:** €**{total_earnings_calc:.2f}**")

        st.markdown("---")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric(label=f"📌 {sel_month_name} {sel_month_year} Toplam Çalışma Saati", value=f"{total_m_hours} Saat")
        with m_col2:
            st.metric(label=f"💶 {sel_month_name} {sel_month_year} Toplam Gider / Malzeme", value=f"€{total_m_cost:.2f}")

        st.markdown("---")
        st.markdown("### 👷 Çalışan Bazlı Aylık Toplamlar")
        df_m_worker = df_m.groupby("Çalışan")["Saat"].sum().reset_index()
        st.markdown(f'<div class="table-container">{df_m_worker.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📁 Proje Bazlı Aylık Toplamlar")
        df_m_proj = df_m.groupby("Proje")["Saat"].sum().reset_index()
        st.markdown(f'<div class="table-container">{df_m_proj.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔍 Proje & Çalışan Aylık Matrisi")
        df_m_pivot = df_m.pivot_table(index="Proje", columns="Çalışan", values="Saat", aggfunc="sum", fill_value=0).reset_index()
        st.markdown(f'<div class="table-container">{df_m_pivot.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
    else:
        st.info(f"{sel_month_name} {sel_month_year} dönemi için seçilen kriterlere uygun kayıt bulunmuyor.")

with tab_entry:
    st.markdown(f"### ⚡ {st.session_state.comp_name}")
    
    col_ey1, col_ey2 = st.columns(2)
    with col_ey1:
        sel_year = st.slider("Yıl Seçimi", 2026, 2035, current_iso_year, key="entry_y_slide")
    with col_ey2:
        week_no = st.slider("Hafta Seçimi", 1, 53, current_iso_week, key="entry_w_slide")
    
    current_week_key = f"{sel_year}-W{week_no}"
    if current_week_key in st.session_state.completed_weeks:
        st.caption("🔴 Bu hafta tamamlandı olarak işaretlendi.")

    st.markdown("---")

    sorted_projects = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    project_options = ["Seçiniz"] + [f"{p['code']} - {p['name']}" for p in sorted_projects]
    worker_options = ["Seçiniz"] + st.session_state.workers

    saved_week_data = st.session_state.weekly_data.get(current_week_key, {"entries": [], "expenses": []})
    
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    
    saved_entries_by_day = {d: [] for d in days}
    for e in saved_week_data.get("entries", []):
        if e.get("Gün") in saved_entries_by_day:
            saved_entries_by_day[e.get("Gün")].append(e)
            
    saved_expenses_by_day = {d: [] for d in days}
    for ex in saved_week_data.get("expenses", []):
        if ex.get("Gün") in saved_expenses_by_day:
            saved_expenses_by_day[ex.get("Gün")].append(ex)

    all_entries = []
    all_expenses = []
    exp_counter = 1

    for day_idx, day in enumerate(days):
        day_date_str = get_date_for_day(sel_year, week_no, day_idx)
        expand_label = f"📌 {day} ({day_to_nl[day]}) - {day_date_str}"
        
        day_entries = saved_entries_by_day.get(day, [])
        saved_projects_for_day = []
        seen_proj = set()
        for e in day_entries:
            p = e.get("Proje")
            if p and p not in seen_proj:
                seen_proj.add(p)
                saved_projects_for_day.append(p)
                
        default_num_proj = max(len(saved_projects_for_day), 1 if day_entries else 0)
        num_proj_key = f"num_proj_{day}_{week_no}"
        if num_proj_key not in st.session_state:
            st.session_state[num_proj_key] = default_num_proj

        with st.expander(expand_label, expanded=(len(day_entries) > 0)):
            num_projects = st.number_input(f"Günlük Proje / Görev Sayısı ({day})", min_value=0, max_value=5, key=num_proj_key)
            
            if num_projects > 0:
                st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 12px 0;'>", unsafe_allow_html=True)

            for p_i in range(int(num_projects)):
                if p_i > 0:
                    st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 16px 0;'>", unsafe_allow_html=True)

                p_key = f"proj_sel_{day}_{p_i}_{week_no}"
                
                default_proj = "Seçiniz"
                if p_i < len(saved_projects_for_day) and saved_projects_for_day[p_i] in project_options:
                    default_proj = saved_projects_for_day[p_i]
                elif day_entries and p_i < len(day_entries):
                    p_val = day_entries[p_i].get("Proje")
                    if p_val in project_options:
                        default_proj = p_val

                if p_key not in st.session_state or st.session_state[p_key] not in project_options:
                    st.session_state[p_key] = default_proj
                
                proj_sel = st.selectbox(f"Proje {p_i+1} ({day})", project_options, key=p_key)

                if proj_sel != "Seçiniz":
                    st.markdown(f"#### 📁 {proj_sel}")
                    
                    proj_entries = [e for e in day_entries if e.get("Proje") == proj_sel]
                    default_num_workers = max(len(proj_entries), 1 if proj_entries else 0)
                    num_w_key = f"num_w_{day}_{p_i}_{week_no}"
                    if num_w_key not in st.session_state:
                        st.session_state[num_w_key] = default_num_workers

                    num_workers = st.number_input(f"Çalışan Sayısı ({proj_sel} - {day})", min_value=0, max_value=5, key=num_w_key)
                    
                    for w_i in range(int(num_workers)):
                        if w_i > 0:
                            st.markdown("<hr style='border: 1px dashed #CBD5E1; margin: 8px 0;'>", unsafe_allow_html=True)
                            
                        w_key = f"w_slide_{day}_{p_i}_{w_i}_{week_no}"
                        s_key = f"s_slide_{day}_{p_i}_{w_i}_{week_no}"
                        pk_key = f"p_slide_{day}_{p_i}_{w_i}_{week_no}"
                        e_key = f"e_slide_{day}_{p_i}_{w_i}_{week_no}"
                        prev_w_key = f"prev_w_{day}_{p_i}_{w_i}_{week_no}"
                        lock_key = f"lock_state_{day}_{p_i}_{w_i}_{week_no}"
                        
                        saved_w_entry = proj_entries[w_i] if w_i < len(proj_entries) else None

                        default_worker = saved_w_entry.get("Çalışan", "Seçiniz") if saved_w_entry else "Seçiniz"
                        if default_worker not in worker_options:
                            default_worker = "Seçiniz"

                        if w_key not in st.session_state or st.session_state[w_key] not in worker_options:
                            st.session_state[w_key] = default_worker

                        wrk = st.selectbox(f"Çalışan {w_i+1} ({proj_sel})", worker_options, key=w_key)

                        prev_w = st.session_state.get(prev_w_key, None)

                        if saved_w_entry and prev_w is None:
                            def_s = saved_w_entry.get("Başlangıç", "07:00")
                            def_p = saved_w_entry.get("Mola", "00:45")
                            def_e = saved_w_entry.get("Bitiş", "15:45")
                            def_locked = saved_w_entry.get("Locked", False)
                        else:
                            if wrk == "Adem":
                                def_s, def_p, def_e = "05:30", "01:45", "17:15"
                            else:
                                def_s, def_p, def_e = "07:00", "00:45", "15:45"
                            def_locked = False

                        if prev_w != wrk and not saved_w_entry:
                            st.session_state[s_key] = def_s
                            st.session_state[pk_key] = def_p
                            st.session_state[e_key] = def_e
                            st.session_state[prev_w_key] = wrk

                        if s_key not in st.session_state:
                            st.session_state[s_key] = saved_w_entry.get("Başlangıç", def_s) if saved_w_entry else def_s
                        if pk_key not in st.session_state:
                            st.session_state[pk_key] = saved_w_entry.get("Mola", def_p) if saved_w_entry else def_p
                        if e_key not in st.session_state:
                            st.session_state[e_key] = saved_w_entry.get("Bitiş", def_e) if saved_w_entry else def_e
                        if lock_key not in st.session_state:
                            st.session_state[lock_key] = def_locked

                        if wrk != "Seçiniz":
                            st.markdown(f"⏱️ **Saatler - {wrk}**")
                            is_locked = st.session_state[lock_key]

                            curr_s = st.session_state.get(s_key, def_s)
                            if curr_s not in start_slots:
                                curr_s = start_slots[0]
                            final_start = st.select_slider(
                                f"Başlangıç {w_i+1}", options=start_slots, value=curr_s, key=f"s_sl_{day}_{p_i}_{w_i}_{week_no}", disabled=is_locked
                            )
                            st.session_state[s_key] = final_start

                            curr_p = st.session_state.get(pk_key, def_p)
                            if curr_p not in pause_slots:
                                curr_p = pause_slots[0]
                            final_pause = st.select_slider(
                                f"Mola {w_i+1}", options=pause_slots, value=curr_p, key=f"p_sl_{day}_{p_i}_{w_i}_{week_no}", disabled=is_locked
                            )
                            st.session_state[pk_key] = final_pause

                            curr_e = st.session_state.get(e_key, def_e)
                            if curr_e not in end_slots:
                                curr_e = end_slots[0]
                            final_stop = st.select_slider(
                                f"Bitiş {w_i+1}", options=end_slots, value=curr_e, key=f"e_sl_{day}_{p_i}_{w_i}_{week_no}", disabled=is_locked
                            )
                            st.session_state[e_key] = final_stop
                            
                            col_lk1, col_lk2 = st.columns([2, 2])
                            with col_lk1:
                                if is_locked:
                                    if st.button("🔓 Saatleri Aç", key=f"unlock_btn_{day}_{p_i}_{w_i}_{week_no}"):
                                        st.session_state[lock_key] = False
                                        st.rerun()
                                else:
                                    if st.button("🔒 Saatleri Kilitle", key=f"lock_btn_{day}_{p_i}_{w_i}_{week_no}"):
                                        st.session_state[lock_key] = True
                                        st.rerun()
                            with col_lk2:
                                if is_locked:
                                    st.markdown("🔴 **Durum: Kilitli**")
                                else:
                                    st.markdown("🟢 **Durum: Düzenlenebilir**")

                            calc_hours = calculate_net_hours(final_start, final_pause, final_stop)
                            st.markdown(f"⏱️ **{wrk}** | Net: **<span style='color:blue'>{calc_hours} saat</span>** ({final_start} - {final_stop}, Mola: {final_pause})", unsafe_allow_html=True)

                            all_entries.append({
                                "Gün": day,
                                "Tarih": day_date_str,
                                "Proje": proj_sel,
                                "Çalışan": wrk,
                                "Başlangıç": final_start,
                                "Mola": final_pause,
                                "Bitiş": final_stop,
                                "Saat": calc_hours,
                                "Locked": is_locked
                            })
                        else:
                            st.info("Lütfen bir çalışan seçin.")

                    st.markdown(f"💶 **Fiş / Gider ({proj_sel})**")
                    day_expenses = [ex for ex in saved_expenses_by_day.get(day, []) if ex.get("Proje") == proj_sel]
                    default_num_exp = len(day_expenses)
                    num_exp_key = f"num_exp_{day}_{p_i}_{week_no}"
                    if num_exp_key not in st.session_state:
                        st.session_state[num_exp_key] = default_num_exp

                    num_exp = st.number_input(f"Fiş Sayısı ({proj_sel})", min_value=0, max_value=5, key=num_exp_key)
                    
                    for j in range(int(num_exp)):
                        saved_exp = day_expenses[j] if j < len(day_expenses) else None
                        
                        e_cols = st.columns([2, 1.5, 2.5])
                        with e_cols[0]:
                            default_desc = saved_exp.get("Açıklama", st.session_state.expense_categories[0]) if saved_exp else st.session_state.expense_categories[0]
                            if default_desc not in st.session_state.expense_categories:
                                default_desc = st.session_state.expense_categories[0]
                            exp_desc = st.selectbox("Gider", st.session_state.expense_categories, index=st.session_state.expense_categories.index(default_desc), key=f"exp_desc_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        with e_cols[1]:
                            default_amt = float(saved_exp.get("Tutar", 10.0)) if saved_exp else 10.0
                            exp_amount = st.number_input("Tutar", min_value=0.0, value=default_amt, step=1.0, key=f"exp_amt_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        with e_cols[2]:
                            exp_file = st.file_uploader("Fiş Yükle", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        
                        exp_b64 = saved_exp.get("Görsel_b64", None) if saved_exp else None
                        if exp_file is not None:
                            try:
                                exp_b64 = base64.b64encode(exp_file.getvalue()).decode('utf-8')
                            except Exception:
                                pass

                        if exp_amount > 0:
                            all_expenses.append({
                                "Gün": day,
                                "Tarih": day_date_str,
                                "Proje": proj_sel,
                                "Kod": saved_exp.get("Kod", f"Doc {exp_counter}") if saved_exp else f"Doc {exp_counter}",
                                "Açıklama": exp_desc,
                                "Tutar": exp_amount,
                                "Görsel_b64": exp_b64
                            })
                            exp_counter += 1
                else:
                    st.info("Lütfen önce bir proje seçin.")

    # --- TAMAMEN OTOMATİK KAYIT ---
    st.session_state.weekly_data[current_week_key] = {"entries": all_entries, "expenses": all_expenses}
    db_save("weekly_data", st.session_state.weekly_data)

    def create_pdf(project_name, entries, expenses, week, year):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
        story = []
        
        primary_color = colors.HexColor('#0F172A')
        accent_color = colors.HexColor('#2563EB')
        light_bg = colors.HexColor('#F8FAFC')
        alt_bg = colors.HexColor('#F1F5F9')
        border_color = colors.HexColor('#CBD5E1')
        text_dark = colors.HexColor('#1E293B')
        
        sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=text_dark, leading=10)
        bold_sub_style = ParagraphStyle('BoldSubStyle', fontName='Helvetica-Bold', fontSize=8, textColor=primary_color, leading=10)
        
        header_left_elements = []
        logo_io = get_logo_io()
        if logo_io is not None:
            try:
                logo_io.seek(0)
                pil_logo = PILImage.open(logo_io)
                img_io = io.BytesIO()
                pil_logo.save(img_io, format='JPEG', quality=95)
                img_io.seek(0)
                rl_img = RLImage(img_io, width=40, height=40)
                header_left_elements.append(rl_img)
            except Exception:
                pass
        
        header_text = f"<b><font size=10 color='#0F172A'>{st.session_state.comp_name}</font></b><br/><font size=7 color='#475569'>{st.session_state.comp_address}<br/>E-mail: {st.session_state.comp_email} | GSM: {st.session_state.comp_gsm}<br/>BTW: {st.session_state.comp_btw}</font>"
        header_left_elements.append(Paragraph(header_text, sub_style))
        
        meta_p_style = ParagraphStyle('MetaRight', fontName='Helvetica', fontSize=8, textColor=text_dark, alignment=2, leading=11)
        header_data = [[header_left_elements, Paragraph(f"<b>Weeknummer:</b> {week} ({year})<br/><b>Project:</b> {project_name}", meta_p_style)]]
        t_header = Table(header_data, colWidths=[270, 275])
        t_header.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.5, accent_color),
            ('BACKGROUND', (0,0), (-1,-1), light_bg),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 8))
        
        day_order = {"Pazartesi": 1, "Salı": 2, "Çarşamba": 3, "Perşembe": 4, "Cuma": 5, "Cumartesi": 6, "Zondag": 7}
        proj_entries = [e for e in entries if e["Proje"] == project_name]
        sorted_entries = sorted(proj_entries, key=lambda x: (x.get("Çalışan", ""), day_order.get(x.get("Gün", ""), 8)))

        table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                          for h in ["Medewerker", "Dag", "Start", "Pauze", "Einde", "Uren"]]]
        
        total_hours = 0
        worker_hours = {}
        for e in sorted_entries:
            d_nl = day_to_nl.get(e["Gün"], e["Gün"])
            d_str = f"{d_nl} ({e['Tarih']})" if e.get('Tarih') else d_nl
            table_content.append([
                Paragraph(f"<b>{e['Çalışan']}</b>", bold_sub_style),
                Paragraph(d_str, sub_style),
                Paragraph(e["Başlangıç"], sub_style),
                Paragraph(e["Mola"], sub_style),
                Paragraph(e["Bitiş"], sub_style),
                Paragraph(str(e["Saat"]), sub_style),
            ])
            total_hours += e["Saat"]
            worker_hours[e["Çalışan"]] = worker_hours.get(e["Çalışan"], 0.0) + e["Saat"]
            
        t_main = Table(table_content, colWidths=[90, 115, 60, 60, 60, 160])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_main)
        story.append(Spacer(1, 8))
        
        proj_expenses = [ex for ex in expenses if ex["Proje"] == project_name]
        total_cost = 0
        if proj_expenses:
            story.append(Paragraph("<b>Materialen en Kosten:</b>", ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=9, textColor=primary_color)))
            story.append(Spacer(1, 3))
            exp_table_content = [[Paragraph("<b>Document</b>", bold_sub_style), Paragraph("<b>Dag</b>", bold_sub_style), Paragraph("<b>Omschrijving</b>", bold_sub_style), Paragraph("<b>Bedrag (€)</b>", bold_sub_style)]]
            for ex in proj_expenses:
                d_nl = day_to_nl.get(ex["Gün"], ex["Gün"])
                d_str = f"{d_nl} ({ex['Tarih']})" if e.get('Tarih') else d_nl
                exp_table_content.append([
                    Paragraph(f"<b>{ex['Kod']}</b>", bold_sub_style),
                    Paragraph(d_str, sub_style),
                    Paragraph(ex["Açıklama"], sub_style),
                    Paragraph(f"€{ex['Tutar']:.2f}", sub_style)
                ])
                total_cost += ex["Tutar"]
            t_exp = Table(exp_table_content, colWidths=[80, 100, 265, 100])
            t_exp.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), alt_bg),
                ('GRID', (0,0), (-1,-1), 0.5, border_color),
                ('PADDING', (0,0), (-1,-1), 4),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t_exp)
            story.append(Spacer(1, 8))

        worker_breakdown_html = "<br/>".join([f"• <b>{w}:</b> {hrs} uur" for w, hrs in worker_hours.items()])
        summary_text = f"<b>Uren per medewerker:</b><br/>{worker_breakdown_html}<br/><br/><b>Totale uren:</b> {total_hours} uur<br/><b>Totale kosten:</b> €{total_cost:.2f}"
        
        t_summary = Table([[Paragraph(summary_text, sub_style), Paragraph("<b>Klantakkoord / Handtekening:</b><br/><br/>___________________", sub_style)]], colWidths=[270, 275])
        t_summary.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('BACKGROUND', (0,0), (-1,-1), light_bg),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_summary)
        
        # --- FİŞ GÖRSELLERİ ---
        valid_expenses_with_img = [ex for ex in proj_expenses if ex.get("Görsel_b64")]
        if valid_expenses_with_img:
            story.append(PageBreak())
            story.append(Paragraph("<b>Bijlagen / Bonnetjes:</b>", ParagraphStyle('ImgHeader', fontName='Helvetica-Bold', fontSize=10, textColor=primary_color)))
            story.append(Spacer(1, 10))

            chunks = [valid_expenses_with_img[i:i + 4] for i in range(0, len(valid_expenses_with_img), 4)]
            
            for chunk_idx, chunk in enumerate(chunks):
                if chunk_idx > 0:
                    story.append(PageBreak())
                    story.append(Paragraph("<b>Bijlagen / Bonnetjes (Vervolg):</b>", ParagraphStyle('ImgHeader', fontName='Helvetica-Bold', fontSize=10, textColor=primary_color)))
                    story.append(Spacer(1, 10))
                
                grid_data = [[None, None], [None, None]]
                
                for idx, ex in enumerate(chunk):
                    row = idx // 2
                    col = idx % 2
                    
                    cell_elements = []
                    try:
                        img_bytes = base64.b64decode(ex["Görsel_b64"])
                        pil_img = PILImage.open(io.BytesIO(img_bytes))
                        pil_img = pil_img.convert("RGB")
                        
                        orig_w, orig_h = pil_img.size
                        max_w = 220
                        max_h = 260
                        aspect = orig_h / orig_w
                        w = max_w
                        h = max_w * aspect
                        if h > max_h:
                            h = max_h
                            w = max_h / aspect

                        d_nl = day_to_nl.get(ex["Gün"], ex["Gün"])
                        caption_text = f"<b>{ex['Kod']}</b> - {ex['Açıklama']} (€{ex['Tutar']:.2f})<br/>{d_nl}"
                        cell_elements.append(Paragraph(caption_text, bold_sub_style))
                        cell_elements.append(Spacer(1, 3))
                        
                        img_io = io.BytesIO()
                        pil_img.save(img_io, format='JPEG', quality=85)
                        img_io.seek(0)
                        
                        cell_elements.append(RLImage(img_io, width=w, height=h))
                    except Exception:
                        cell_elements.append(Paragraph(f"Image load error: {ex.get('Kod', '')}", sub_style))
                    
                    grid_data[row][col] = cell_elements
                
                for r in range(2):
                    for c in range(2):
                        if grid_data[r][c] is None:
                            grid_data[r][c] = [Paragraph("", sub_style)]
                
                t_grid = Table(grid_data, colWidths=[260, 260])
                t_grid.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('PADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, border_color),
                ]))
                story.append(t_grid)

        doc.build(story)
        buffer.seek(0)
        return buffer

    st.markdown("---")
    st.markdown("### 📄 Rapor Oluşturma, İndirme ve Önizleme")
    
    active_projects = set([e["Proje"] for e in all_entries] + [ex["Proje"] for ex in all_expenses])
    if active_projects:
        for proj in active_projects:
            pdf_file = create_pdf(proj, all_entries, all_expenses, week_no, sel_year)
            pdf_bytes = pdf_file.getvalue()
            pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_filename = f"Werkbon_Week{week_no}_{sel_year}_{proj.replace(' ', '_').replace('(', '').replace(')', '')}.pdf"
            
            st.session_state.pdf_archive[pdf_filename] = pdf_b64
            db_save("pdf_archive", st.session_state.pdf_archive)
            
            col_dl1, col_dl2, col_dl3 = st.columns([2, 1, 1])
            with col_dl1:
                st.download_button(
                    label=f"📥 {proj} - İndir",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key=f"dl_{proj}_{week_no}"
                )
            with col_dl2:
                pdf_data_url = f"data:application/pdf;base64,{pdf_b64}"
                st.markdown(f'<a href="{pdf_data_url}" target="_blank" style="display:inline-block;padding:0.4rem 0.8rem;background-color:#2563EB;color:white;text-decoration:none;border-radius:4px;font-size:12px;font-weight:bold;text-align:center;width:100%;">🔍 Önizle</a>', unsafe_allow_html=True)
            with col_dl3:
                if current_week_key in st.session_state.completed_weeks:
                    if st.button("🔄 Aç", key=f"unmark_{proj}_{week_no}"):
                        st.session_state.completed_weeks.remove(current_week_key)
                        db_save("completed_weeks", list(st.session_state.completed_weeks))
                        st.rerun()
                else:
                    if st.button("✅ Tamamla", key=f"mark_{proj}_{week_no}"):
                        st.session_state.completed_weeks.add(current_week_key)
                        db_save("completed_weeks", list(st.session_state.completed_weeks))
                        st.rerun()
    else:
        st.info("Bu hafta için henüz kayıt girilmedi.")
