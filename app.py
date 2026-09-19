import streamlit as st
import pandas as pd
import json
import sqlite3
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage, ImageDraw, ImageFont
from datetime import datetime, timedelta

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

# --- VERİTABANI BAĞLANTI VE BAŞLANGIÇ İŞLEMLERİ ---
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

st.markdown("""
    <style>
    /* MOBİL İÇİN YATAY KAYDIRILABİLİR (SWIPE) BUTON TASARIMI */
    div[data-testid="stPills"] [role="radiogroup"] {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 8px; /* Kaydırma çubuğu için boşluk */
        gap: 6px;
    }
    
    /* İnce, zarif bir yatay kaydırma çubuğu ekliyoruz */
    div[data-testid="stPills"] [role="radiogroup"]::-webkit-scrollbar {
        height: 4px;
    }
    div[data-testid="stPills"] [role="radiogroup"]::-webkit-scrollbar-thumb {
        background-color: #CBD5E1;
        border-radius: 4px;
    }
    div[data-testid="stPills"] [role="radiogroup"]::-webkit-scrollbar-track {
        background-color: transparent;
    }
    
    /* Buton içindeki yazıların alt satıra düşmemesi için */
    div[data-testid="stPills"] label {
        white-space: nowrap !important;
        font-size: 13px !important;
        padding: 4px 12px !important;
    }

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

# Geniş Saat Slotları (Eski bol ve geniş seçeneklerine geri döndürüldü)
start_slots = ["05:00", "05:30", "06:00", "06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "Manuel"]
end_slots = ["14:00", "14:30", "15:00", "15:30", "15:45", "16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30", "18:00", "19:00", "Manuel"]
pause_slots = ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45", "02:00", "Manuel"]

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
    st.header("⚙️ Ayarlar ve Veri Yönetimi")
    
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
    st.subheader("💾 Yedekleme")
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
                # Projeyi silme özelliği
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
                # Arşivdeki PDF'yi silme özelliği
                if st.button("🗑️ Sil", key=f"arch_del_{filename}"):
                    del st.session_state.pdf_archive[filename]
                    db_save("pdf_archive", st.session_state.pdf_archive)
                    st.rerun()
    else:
        st.info("Arşiv boş.")

today = datetime.today()
current_iso_year, current_iso_week, _ = today.isocalendar()

years_list = [str(y) for y in range(2026, 2036)]
weeks_list = [str(w) for w in range(1, 54)]

with tab_preview:
    st.header("📊 Haftalık Özet")
    
    if "prev_y_pill" not in st.session_state: st.session_state["prev_y_pill"] = str(current_iso_year)
    if "prev_w_pill" not in st.session_state: st.session_state["prev_w_pill"] = str(current_iso_week)
    
    # Yıl ve Hafta yatay kaydırma ile (Özet)
    prev_sel_year_str = st.pills("Yıl Seçiniz (Sağa kaydırabilirsiniz)", years_list, key="prev_y_pill")
    prev_sel_year = int(prev_sel_year_str) if prev_sel_year_str else current_iso_year
    
    prev_week_no_str = st.pills("Hafta Seçiniz", weeks_list, key="prev_w_pill")
    prev_week_no = int(prev_week_no_str) if prev_week_no_str else current_iso_week
        
    wk_key = f"{prev_sel_year}-W{prev_week_no}"
    w_data = st.session_state.weekly_data.get(wk_key, {"entries": [], "expenses": []})
    if w_data["entries"]:
        df_p = pd.DataFrame(w_data["entries"])
        st.markdown(f'<div class="table-container">{df_p[["Gün", "Tarih", "Proje", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
    else:
        st.info("Kayıt yok.")

with tab_entry:
    st.markdown(f"### ⚡ {st.session_state.comp_name}")
    
    if "entry_y" not in st.session_state: st.session_state["entry_y"] = str(current_iso_year)
    if "entry_w" not in st.session_state: st.session_state["entry_w"] = str(current_iso_week)

    # Yıl ve Hafta yatay kaydırma ile (Veri Girişi)
    sel_year_str = st.pills("Yıl (Kaydırın ↔️)", years_list, key="entry_y")
    sel_year = int(sel_year_str) if sel_year_str else current_iso_year
    
    week_no_str = st.pills("Hafta Seçimi (Kaydırın ↔️)", weeks_list, key="entry_w")
    week_no = int(week_no_str) if week_no_str else current_iso_week
    
    current_week_key = f"{sel_year}-W{week_no}"
    if current_week_key in st.session_state.completed_weeks:
        st.caption("🔴 Bu hafta tamamlandı olarak işaretlendi.")

    st.markdown("---")

    sorted_projects = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    project_options = [f"{p['code']} - {p['name']}" for p in sorted_projects] or ["E260000 - Genel"]

    saved_week_data = st.session_state.weekly_data.get(current_week_key, {"entries": [], "expenses": []})
    entries_by_day = {}
    for e in saved_week_data.get("entries", []):
        entries_by_day.setdefault(e["Gün"], []).append(e)

    expenses_by_day = {}
    for ex in saved_week_data.get("expenses", []):
        expenses_by_day.setdefault(ex["Gün"], []).append(ex)

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []
    exp_counter = 1

    # Çalışan değiştiğinde diğer saatleri otomatikleştiren fonksiyon
    def update_worker_defaults(day_name, row_idx, wk_no):
        w_k = f"w_pill_{day_name}_{row_idx}_{wk_no}"
        s_k = f"s_pill_{day_name}_{row_idx}_{wk_no}"
        p_k = f"p_pill_{day_name}_{row_idx}_{wk_no}"
        e_k = f"e_pill_{day_name}_{row_idx}_{wk_no}"
        
        sel_w = st.session_state.get(w_k)
        if sel_w == "Adem":
            st.session_state[s_k] = "05:30"
            st.session_state[p_k] = "01:45"
            st.session_state[e_k] = "17:15"
        elif sel_w:
            st.session_state[s_k] = "07:00"
            st.session_state[p_k] = "00:45"
            st.session_state[e_k] = "15:45"

    for day_idx, day in enumerate(days):
        day_date_str = get_date_for_day(sel_year, week_no, day_idx)
        expand_label = f"📌 {day} ({day_to_nl[day]}) - {day_date_str}"
        
        d_entries = entries_by_day.get(day, [])
        d_exp = expenses_by_day.get(day, [])
        
        with st.expander(expand_label, expanded=False):
            def_p_idx = 0
            if d_entries and d_entries[0].get("Proje") in project_options:
                def_p_idx = project_options.index(d_entries[0]["Proje"])

            day_proj = st.selectbox(f"Proje ({day})", project_options, index=def_p_idx, key=f"day_proj_{day}_{week_no}")
            num_rows = st.number_input(f"Çalışan Sayısı ({day})", min_value=0, max_value=8, value=len(d_entries), key=f"num_{day}_{week_no}")
            
            if num_rows > 0:
                st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 12px 0;'>", unsafe_allow_html=True)

            for i in range(int(num_rows)):
                if i > 0:
                    st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 12px 0;'>", unsafe_allow_html=True)

                saved_e = d_entries[i] if i < len(d_entries) else {}
                
                w_key = f"w_pill_{day}_{i}_{week_no}"
                s_key = f"s_pill_{day}_{i}_{week_no}"
                p_key = f"p_pill_{day}_{i}_{week_no}"
                e_key = f"e_pill_{day}_{i}_{week_no}"
                
                # Başlangıç değerleri (Çalışan için)
                if w_key not in st.session_state:
                    st.session_state[w_key] = saved_e.get("Çalışan", st.session_state.workers[0] if st.session_state.workers else None)
                init_w = st.session_state[w_key]

                # Saati güvenli şekilde ayarlayan yardımcı fonksiyon
                def get_initial_val(saved_val, default_adem, default_other, valid_slots):
                    val = saved_val if saved_val else (default_adem if init_w == "Adem" else default_other)
                    return val if val in valid_slots else "Manuel"

                if s_key not in st.session_state:
                    st.session_state[s_key] = get_initial_val(saved_e.get("Başlangıç"), "05:30", "07:00", start_slots)
                if p_key not in st.session_state:
                    st.session_state[p_key] = get_initial_val(saved_e.get("Mola"), "01:45", "00:45", pause_slots)
                if e_key not in st.session_state:
                    st.session_state[e_key] = get_initial_val(saved_e.get("Bitiş"), "17:15", "15:45", end_slots)

                # Çalışan Seçimi (Yine kaydırmalı buton ile klavye sıfırlanır)
                wrk = st.pills(f"Çalışan {i+1}", st.session_state.workers, key=w_key, on_change=update_worker_defaults, args=(day, i, week_no))
                
                # Yatay kaydırılabilir saat seçenekleri
                s_choice = st.pills(f"Başlangıç (Kaydırın ↔️)", start_slots, key=s_key)
                start_manual = st.text_input(f"M. Başlangıç", value=saved_e.get("Başlangıç", "07:00"), key=f"s_man_{day}_{i}_{week_no}")
                start = start_manual if s_choice == "Manuel" else (s_choice if s_choice else "00:00")

                p_choice = st.pills(f"Mola (Kaydırın ↔️)", pause_slots, key=p_key)
                pause_manual = st.text_input(f"M. Mola", value=saved_e.get("Mola", "00:45"), key=f"p_man_{day}_{i}_{week_no}")
                pause = pause_manual if p_choice == "Manuel" else (p_choice if p_choice else "00:00")

                e_choice = st.pills(f"Bitiş (Kaydırın ↔️)", end_slots, key=e_key)
                stop_manual = st.text_input(f"M. Bitiş", value=saved_e.get("Bitiş", "15:45"), key=f"e_man_{day}_{i}_{week_no}")
                stop = stop_manual if e_choice == "Manuel" else (e_choice if e_choice else "00:00")
                
                calc_hours = calculate_net_hours(start, pause, stop)
                st.markdown(f"⏱️ **{wrk or 'Seçilmedi'}** | Net: **<span style='color:blue'>{calc_hours} saat</span>**", unsafe_allow_html=True)

                if day_proj and wrk:
                    all_entries.append({
                        "Gün": day,
                        "Tarih": day_date_str,
                        "Proje": day_proj,
                        "Çalışan": wrk,
                        "Başlangıç": start,
                        "Mola": pause,
                        "Bitiş": stop,
                        "Saat": calc_hours
                    })
            
            if num_rows > 0:
                st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 12px 0;'>", unsafe_allow_html=True)
                
            # Gider / Fiş Ekleme Bölümü
            num_exp = st.number_input(f"Fiş/Gider Sayısı ({day})", min_value=0, max_value=5, value=len(d_exp), key=f"num_exp_{day}_{week_no}")
            for j in range(int(num_exp)):
                saved_ex = d_exp[j] if j < len(d_exp) else {}
                e_cols = st.columns([2, 1.5, 2.5])
                with e_cols[0]:
                    exp_desc = st.selectbox("Gider", st.session_state.expense_categories, key=f"exp_desc_{day}_{j}_{week_no}", label_visibility="collapsed")
                with e_cols[1]:
                    exp_amount = st.number_input("Tutar", min_value=0.0, value=float(saved_ex.get("Tutar", 10.0)), step=1.0, key=f"exp_amt_{day}_{j}_{week_no}", label_visibility="collapsed")
                with e_cols[2]:
                    exp_file = st.file_uploader("Fiş", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{j}_{week_no}", label_visibility="collapsed")
                
                exp_b64 = saved_ex.get("Görsel_b64", None)
                if exp_file is not None:
                    try:
                        exp_b64 = base64.b64encode(exp_file.getvalue()).decode('utf-8')
                    except Exception:
                        pass

                if exp_amount > 0 and day_proj:
                    all_expenses.append({
                        "Gün": day,
                        "Tarih": day_date_str,
                        "Proje": day_proj,
                        "Kod": saved_ex.get("Kod", f"Doc {exp_counter}"),
                        "Açıklama": exp_desc,
                        "Tutar": exp_amount,
                        "Görsel_b64": exp_b64
                    })
                    exp_counter += 1

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
        
        header_text = f"<b><font size=10 color='#0F172A'>{st.session_state.comp_name}</font></b><br/><font size=7 color='#475569'>{st.session_state.comp_address}<br/>BTW: {st.session_state.comp_btw}</font>"
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
        sorted_entries = sorted(entries, key=lambda x: (x.get("Çalışan", ""), day_order.get(x.get("Gün", ""), 8)))

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
                d_str = f"{d_nl} ({ex['Tarih']})" if ex.get('Tarih') else d_nl
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
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    st.markdown("---")
    st.markdown("### 📄 Rapor Oluşturma")
    
    if all_entries or all_expenses:
        if st.button("🚀 PDF Raporlarını Oluştur", type="primary", key=f"btn_pdf_{week_no}"):
            st.success("PDF raporları başarıyla oluşturuldu ve arşive eklendi!")
            st.rerun()
            
        active_projects = set([e["Proje"] for e in all_entries] + [ex["Proje"] for ex in all_expenses])
        if active_projects:
            for proj in active_projects:
                p_entries = [e for e in all_entries if e["Proje"] == proj]
                pdf_file = create_pdf(proj, p_entries, all_expenses, week_no, sel_year)
                pdf_bytes = pdf_file.getvalue()
                pdf_filename = f"Werkbon_Week{week_no}_{sel_year}_{proj.replace(' ', '_').replace('(', '').replace(')', '')}.pdf"
                
                st.session_state.pdf_archive[pdf_filename] = base64.b64encode(pdf_bytes).decode('utf-8')
                db_save("pdf_archive", st.session_state.pdf_archive)
                
                col_dl1, col_dl2 = st.columns([3, 1])
                with col_dl1:
                    st.download_button(
                        label=f"📥 {proj} - İndir (Week {week_no})",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"dl_{proj}_{week_no}"
                    )
                with col_dl2:
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
