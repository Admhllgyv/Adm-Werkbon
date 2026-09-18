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
    .stTabs {
        margin-top: 25px !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 8px;
        padding-top: 10px;
    }
    .block-container {
        padding-left: 0.8rem;
        padding-right: 1.8rem;
        padding-top: 1.5rem;
        max-width: 100%;
    }
    html, body, [class*="st-"] {
        font-size: 13px !important;
    }
    h1 {
        font-size: 1.4rem !important;
        white-space: nowrap;
    }
    h2 {
        font-size: 1.2rem !important;
    }
    h3 {
        font-size: 1.0rem !important;
    }
    .streamlit-expanderHeader {
        border: 2px solid #1F4E78 !important;
        border-radius: 6px !important;
        background-color: #F8F9FA !important;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Session State & DB Senkronizasyonu
if 'comp_name' not in st.session_state:
    st.session_state.comp_name = db_load("comp_name", "ADM TECHNICS")
if 'comp_address' not in st.session_state:
    st.session_state.comp_address = db_load("comp_address", "Schutveststraat 5, 3500 Diepenbeek")
if 'comp_btw' not in st.session_state:
    st.session_state.comp_btw = db_load("comp_btw", "BE0787743276")
if 'comp_logo_b64' not in st.session_state:
    st.session_state.comp_logo_b64 = db_load("comp_logo_b64", None)

def get_logo_io():
    if st.session_state.comp_logo_b64:
        try:
            return io.BytesIO(base64.b64decode(st.session_state.comp_logo_b64))
        except Exception:
            return None
    return None

if 'workers' not in st.session_state:
    st.session_state.workers = db_load("workers", ["Adem", "Melih"])

if 'projects' not in st.session_state:
    st.session_state.projects = db_load("projects", [
        {"name": "Kruidvat Diepenbeek", "code": "E260001"},
        {"name": "ICI PARIS XL Hasselt", "code": "E260002"}
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

def generate_time_slots(start_time_str, end_time_str):
    slots = []
    current = datetime.strptime(start_time_str, "%H:%M")
    limit = datetime.strptime(end_time_str, "%H:%M")
    while current <= limit:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=15)
    slots.append("Manuel Giriş")
    return slots

start_slots = generate_time_slots("03:45", "09:00")
end_slots = generate_time_slots("12:00", "19:00")
pause_slots = ["00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45", "02:00", "Manuel Giriş"]

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
    "📝 Werkbon Girişi", "📊 Haftalık Özet", "📁 Proje Yönetimi", "📚 PDF Arşivi", "⚙️ Ayarlar"
])

with tab_settings:
    st.header("⚙️ Firma, Çalışan, Gider ve Veri Yedekleme")
    
    st.subheader("Firma Bilgileri ve Logosu")
    logo_io = get_logo_io()
    if logo_io is not None:
        st.image(logo_io, width=100, caption="Mevcut Firma Logosu")
        
    uploaded_logo = st.file_uploader("Firma Logosu Yükle veya Değiştir (JPG / PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        try:
            b64_str = base64.b64encode(uploaded_logo.getvalue()).decode('utf-8')
            st.session_state.comp_logo_b64 = b64_str
            db_save("comp_logo_b64", b64_str)
            st.success("Logo başarıyla kaydedildi ve güncellendi!")
            st.rerun()
        except Exception as e:
            st.error(f"Logo yüklenirken hata oluştu: {e}")

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
    st.subheader("💾 Veri Yedekleme ve Güvenlik")
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
        label="📥 Tüm Verileri Telefonuma Yedekle (JSON)",
        data=json_str,
        file_name=f"adm_technics_backup_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

    uploaded_backup = st.file_uploader("📂 Daha Önce Aldığın Yedeği Geri Yükle", type=["json"])
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
            st.success("Tüm veriler başarıyla geri yüklendi!")
            st.rerun()
        except Exception as e:
            st.error(f"Yedek yüklenirken hata oluştu: {e}")

    st.markdown("---")
    st.subheader("Çalışan Listesi")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        new_w = st.text_input("Yeni Çalışan")
    with col_w2:
        st.write("")
        st.write("")
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
    st.subheader("Gider / Malzeme Açıklamaları")
    col_e1, col_e2 = st.columns([2, 1])
    with col_e1:
        new_exp_desc = st.text_input("Yeni Gider Tanımı")
    with col_e2:
        st.write("")
        st.write("")
        if st.button("Gider Tanımı Ekle"):
            if new_exp_desc and new_exp_desc not in st.session_state.expense_categories:
                st.session_state.expense_categories.append(new_exp_desc)
                db_save("expense_categories", st.session_state.expense_categories)
                st.rerun()
    for ec in st.session_state.expense_categories:
        cec = st.columns([3, 1])
        cec[0].write(f"- {ec}")
        if len(st.session_state.expense_categories) > 1 and cec[1].button("Sil", key=f"del_ec_{ec}"):
            st.session_state.expense_categories.remove(ec)
            db_save("expense_categories", st.session_state.expense_categories)
            st.rerun()

with tab_projects:
    st.header("📁 Proje Yönetimi, Düzenleme ve Arşiv")
    st.markdown("Buradan mevcut projelerinizi güncelleyebilir, yazım hatalarını düzeltebilir veya silebilirsiniz.")
    
    with st.form("add_project_form"):
        p_name = st.text_input("Proje / Müşteri Adı")
        p_code = st.text_input("Proje Numarası / Kodu (Örn: E260003)")
        submitted = st.form_submit_button("Yeni Proje Kaydet")
        if submitted and p_name:
            st.session_state.projects.append({"name": p_name, "code": p_code if p_code else "E260000"})
            db_save("projects", st.session_state.projects)
            st.success(f"'{p_name}' başarıyla eklendi!")
            st.rerun()
            
    st.subheader("Mevcut Projeler (Düzenle / Sil)")
    sorted_projects = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    
    for idx, prj in enumerate(sorted_projects):
        with st.expander(f"📌 {prj['code']} - {prj['name']}"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                upd_name = st.text_input("Proje Adı Düzenle", value=prj['name'], key=f"upd_name_{idx}")
            with col_u2:
                upd_code = st.text_input("Proje Kodu Düzenle", value=prj['code'], key=f"upd_code_{idx}")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Güncellemeyi Kaydet", key=f"save_p_{idx}"):
                    for p in st.session_state.projects:
                        if p['code'] == prj['code'] and p['name'] == prj['name']:
                            p['name'] = upd_name
                            p['code'] = upd_code
                    db_save("projects", st.session_state.projects)
                    st.success("Proje güncellendi!")
                    st.rerun()
            with col_btn2:
                if len(st.session_state.projects) > 1:
                    if st.button("Projeyi Sil", key=f"del_p_{idx}"):
                        st.session_state.projects = [p for p in st.session_state.projects if not (p['code'] == prj['code'] and p['name'] == prj['name'])]
                        db_save("projects", st.session_state.projects)
                        st.warning("Proje silindi!")
                        st.rerun()
                else:
                    st.info("En az 1 proje kalmalıdır.")

with tab_archive:
    st.header("📚 PDF Arşivi (İndirilenler Merkezi)")
    st.markdown("Oluşturduğunuz ve indirdiğiniz tüm PDF raporları burada saklanır.")
    
    if st.session_state.pdf_archive:
        for filename, b64_pdf in list(st.session_state.pdf_archive.items()):
            col_ar1, col_ar2 = st.columns([3, 1])
            with col_ar1:
                st.write(f"📄 **{filename}**")
            with col_ar2:
                try:
                    pdf_bytes = base64.b64decode(b64_pdf)
                    st.download_button(
                        label="📥 İndir",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"dl_arch_{filename}"
                    )
                except Exception:
                    pass
        if st.button("🗑️ Arşivi Temizle"):
            st.session_state.pdf_archive = {}
            db_save("pdf_archive", {})
            st.success("Arşiv temizlendi.")
            st.rerun()
    else:
        st.info("Henüz arşivde PDF bulunmuyor. Haftalık rapor oluşturup indirdiğinizde buraya eklenecektir.")

# --- GÜNCEL TARİH VE HAFTA BİLGİSİ ---
today = datetime.today()
current_iso_year, current_iso_week, _ = today.isocalendar()

with tab_preview:
    st.header("📊 Kim Nerede Ne Kadar Çalıştı? (Haftalık Özet)")
    st.markdown("Seçilen haftaya ait çalışan, proje ve saat dağılımlarını aşağıdan takip edebilirsin.")
    
    col_pyr, col_pwk = st.columns(2)
    with col_pyr:
        prev_sel_year = st.selectbox("Özet Yılı", list(range(2026, 2036)), index=0, key="prev_year")
    with col_pwk:
        week_options = list(range(1, 54))
        default_prev_idx = current_iso_week - 1 if prev_sel_year == current_iso_year and 1 <= current_iso_week <= 53 else 0
        prev_week_no = st.selectbox("Özet Hafta No", week_options, index=default_prev_idx, key="prev_week")
        
    prev_week_key = f"{prev_sel_year}-W{prev_week_no}"
    week_stored_data = st.session_state.weekly_data.get(prev_week_key, {"entries": [], "expenses": []})
    p_entries = week_stored_data.get("entries", [])
    p_expenses = week_stored_data.get("expenses", [])
    
    if p_entries:
        df_p = pd.DataFrame(p_entries)
        
        st.markdown("---")
        st.subheader("👥 Çalışan Bazlı Toplam Saatler")
        worker_totals = df_p.groupby("Çalışan")["Saat"].sum().reset_index()
        st.dataframe(worker_totals, use_container_width=True)
        
        st.subheader("📌 Proje Bazlı Toplam Saatler")
        project_totals = df_p.groupby("Proje")["Saat"].sum().reset_index()
        st.dataframe(project_totals, use_container_width=True)
        
        st.subheader("📋 Detaylı Çalışma Listesi")
        st.dataframe(df_p[["Gün", "Tarih", "Proje", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]], use_container_width=True)
    else:
        st.info(f"Week {prev_week_no} ({prev_sel_year}) için henüz kayıt bulunmuyor.")
        
    if p_expenses:
        st.markdown("---")
        st.subheader("🏷️ Bu Haftaya Ait Giderler ve Fişler")
        df_exp = pd.DataFrame(p_expenses)
        st.dataframe(df_exp[["Gün", "Tarih", "Proje", "Kod", "Açıklama", "Tutar"]], use_container_width=True)

with tab_entry:
    st.markdown(f"### ⚡ {st.session_state.comp_name} Werkbon")
    
    col_yr, col_wk = st.columns(2)
    with col_yr:
        sel_year = st.selectbox("Yıl", list(range(2026, 2036)), index=0)
    with col_wk:
        week_options = list(range(1, 54))
        formatted_week_options = []
        default_week_idx = current_iso_week - 1 if current_iso_week <= 53 else 0
        
        for idx, w in enumerate(week_options):
            w_key = f"{sel_year}-W{w}"
            if w_key in st.session_state.completed_weeks:
                status_label = f"🔴 Week {w} [Tamamlandı]"
            else:
                status_label = f"Week {w}"
            formatted_week_options.append((w, status_label))
            if w == current_iso_week and sel_year == current_iso_year:
                default_week_idx = idx
        
        selected_week_tuple = st.selectbox(
            "Hafta Seçimi (Weeknummer)", 
            options=formatted_week_options, 
            format_func=lambda x: f"{x[1]} ({sel_year})",
            index=default_week_idx
        )
        week_no = selected_week_tuple[0]
        current_week_key = f"{sel_year}-W{week_no}"

    st.markdown("---")

    sorted_projects_dropdown = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    project_options = [f"{p['code']} - {p['name']}" for p in sorted_projects_dropdown]
    if not project_options:
        project_options = ["E260000 - Genel Proje"]

    # Seçilen haftanın önceden kaydedilmiş verilerini çekiyoruz
    saved_week_data = st.session_state.weekly_data.get(current_week_key, {"entries": [], "expenses": []})
    saved_entries = saved_week_data.get("entries", [])
    saved_expenses = saved_week_data.get("expenses", [])

    entries_by_day = {}
    for e in saved_entries:
        entries_by_day.setdefault(e["Gün"], []).append(e)

    expenses_by_day = {}
    for ex in saved_expenses:
        expenses_by_day.setdefault(ex["Gün"], []).append(ex)

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []
    exp_counter = 1

    for day_idx, day in enumerate(days):
        day_date_str = get_date_for_day(sel_year, week_no, day_idx)
        expand_label = f"📌 {day} ({day_to_nl[day]}) - {day_date_str}" if day_date_str else f"📌 {day} ({day_to_nl[day]})"
        
        day_saved_entries = entries_by_day.get(day, [])
        day_saved_exp = expenses_by_day.get(day, [])
        
        with st.expander(expand_label, expanded=False):
            # Proje seçimi varsayılanı
            default_proj_idx = 0
            if day_saved_entries:
                saved_proj = day_saved_entries[0].get("Proje")
                if saved_proj in project_options:
                    default_proj_idx = project_options.index(saved_proj)

            day_proj = st.selectbox(f"📌 {day} Projesi", project_options, index=default_proj_idx, key=f"day_proj_{day}_{week_no}")

            num_rows = st.number_input(f"{day} çalışma satırı sayısı", min_value=0, max_value=10, value=len(day_saved_entries), key=f"num_{day}_{week_no}")
            
            for i in range(int(num_rows)):
                saved_e = day_saved_entries[i] if i < len(day_saved_entries) else {}
                
                w_list = st.session_state.workers
                w_val = saved_e.get("Çalışan", w_list[0] if w_list else "")
                w_idx = w_list.index(w_val) if w_val in w_list else 0
                
                s_val = saved_e.get("Başlangıç", "07:00")
                s_idx = start_slots.index(s_val) if s_val in start_slots else 0
                
                p_val = saved_e.get("Mola", "00:45")
                p_idx = pause_slots.index(p_val) if p_val in pause_slots else 2
                
                e_val = saved_e.get("Bitiş", "15:45")
                e_idx = end_slots.index(e_val) if e_val in end_slots else 0

                cols = st.columns([2, 1.2, 1.2, 1.2])
                with cols[0]:
                    wrk = st.selectbox("Çalışan", w_list, index=w_idx, key=f"w_{day}_{i}_{week_no}")
                with cols[1]:
                    s_choice = st.selectbox("Başlangıç", start_slots, index=s_idx, key=f"s_choice_{day}_{i}_{week_no}")
                    start = st.text_input("Örn: 07:00", value=s_val if s_choice == "Manuel Giriş" else "07:00", key=f"s_man_{day}_{i}_{week_no}") if s_choice == "Manuel Giriş" else s_choice
                with cols[2]:
                    p_choice = st.selectbox("Mola", pause_slots, index=p_idx, key=f"p_choice_{day}_{i}_{week_no}")
                    pause = st.text_input("Örn: 00:45", value=p_val if p_choice == "Manuel Giriş" else "00:45", key=f"p_man_{day}_{i}_{week_no}") if p_choice == "Manuel Giriş" else p_choice
                with cols[3]:
                    e_choice = st.selectbox("Bitiş", end_slots, index=e_idx, key=f"e_choice_{day}_{i}_{week_no}")
                    stop = st.text_input("Örn: 15:45", value=e_val if e_choice == "Manuel Giriş" else "15:45", key=f"e_man_{day}_{i}_{week_no}") if e_choice == "Manuel Giriş" else e_choice
                
                calculated_hours = calculate_net_hours(start, pause, stop)
                st.caption(f"⏱️ Net: **{calculated_hours} saat** ({start} - {stop}, Mola: {pause})")

                if day_proj:
                    all_entries.append({
                        "Gün": day,
                        "Tarih": day_date_str,
                        "Proje": day_proj,
                        "Çalışan": wrk,
                        "Başlangıç": start,
                        "Mola": pause,
                        "Bitiş": stop,
                        "Saat": calculated_hours
                    })
            
            st.markdown("---")
            st.markdown(f"🏷️ **{day} - Fatura / Gider Ekleme**")
            num_exp = st.number_input(f"{day} gider/fiş sayısı", min_value=0, max_value=5, value=len(day_saved_exp), key=f"num_exp_{day}_{week_no}")
            
            for j in range(int(num_exp)):
                saved_ex = day_saved_exp[j] if j < len(day_saved_exp) else {}
                
                exp_desc_val = saved_ex.get("Açıklama", st.session_state.expense_categories[0] if st.session_state.expense_categories else "")
                exp_desc_idx = st.session_state.expense_categories.index(exp_desc_val) if exp_desc_val in st.session_state.expense_categories else 0
                
                exp_amt_val = float(saved_ex.get("Tutar", 10.0))
                existing_b64 = saved_ex.get("Görsel_b64", None)

                e_cols = st.columns([1.5, 1.5, 2.5])
                with e_cols[0]:
                    exp_desc = st.selectbox("Gider Açıklaması", st.session_state.expense_categories, index=exp_desc_idx, key=f"exp_desc_{day}_{j}_{week_no}")
                with e_cols[1]:
                    exp_amount = st.number_input("Tutar (€)", min_value=0.0, value=exp_amt_val, step=1.0, key=f"exp_amt_{day}_{j}_{week_no}")
                with e_cols[2]:
                    if existing_b64:
                        st.caption("📷 Mevcut Fiş Yüklü")
                    exp_file = st.file_uploader(f"Fiş Görseli", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{j}_{week_no}")
                
                exp_file_b64 = existing_b64
                if exp_file is not None:
                    try:
                        exp_file_b64 = base64.b64encode(exp_file.getvalue()).decode('utf-8')
                    except Exception:
                        pass

                if exp_amount > 0 and day_proj:
                    doc_code = saved_ex.get("Kod", f"Document {exp_counter}")
                    exp_counter += 1
                    all_expenses.append({
                        "Gün": day,
                        "Tarih": day_date_str,
                        "Proje": day_proj,
                        "Kod": doc_code,
                        "Açıklama": exp_desc,
                        "Tutar": exp_amount,
                        "Görsel_b64": exp_file_b64
                    })

    st.session_state.weekly_data[current_week_key] = {
        "entries": all_entries,
        "expenses": all_expenses
    }
    db_save("weekly_data", st.session_state.weekly_data)

    # --- PDF OLUŞTURMA FONKSİYONU ---
    def create_pdf(project_name, entries, expenses, week, year):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        
        sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555555'))
        
        header_left_elements = []
        logo_io = get_logo_io()
        if logo_io is not None:
            try:
                logo_io.seek(0)
                pil_logo = PILImage.open(logo_io)
                img_io = io.BytesIO()
                pil_logo.save(img_io, format='JPEG')
                img_io.seek(0)
                rl_img = RLImage(img_io, width=40, height=40)
                header_left_elements.append(rl_img)
            except Exception:
                pass
        
        header_text = f"<b>{st.session_state.comp_name}</b><br/><font size=7>{st.session_state.comp_address}<br/>BTW: {st.session_state.comp_btw}</font>"
        header_left_elements.append(Paragraph(header_text, sub_style))
        
        header_data = [
            [
                header_left_elements,
                Paragraph(f"<b>Weeknummer:</b> {week} ({year})<br/><b>Project / Klant:</b> {project_name}", ParagraphStyle('Meta', fontName='Helvetica', fontSize=8, alignment=2))
            ]
        ]
        t_header = Table(header_data, colWidths=[250, 285])
        t_header.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F4F8')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 10))
        
        table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                          for h in ["Dag", "Medewerker", "Start", "Pauze", "Einde", "Uren"]]]
        
        total_hours = 0
        for e in entries:
            d_nl = day_to_nl.get(e["Gün"], e["Gün"])
            d_str = f"{d_nl} ({e['Tarih']})" if e.get('Tarih') else d_nl
            table_content.append([
                Paragraph(d_str, sub_style),
                Paragraph(e["Çalışan"], sub_style),
                Paragraph(e["Başlangıç"], sub_style),
                Paragraph(e["Mola"], sub_style),
                Paragraph(e["Bitiş"], sub_style),
                Paragraph(str(e["Saat"]), sub_style),
            ])
            total_hours += e["Saat"]
            
        t_main = Table(table_content, colWidths=[110, 85, 65, 65, 65, 140])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E78')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_main)
        story.append(Spacer(1, 10))
        
        proj_expenses = [ex for ex in expenses if ex["Proje"] == project_name]
        total_cost = 0
        if proj_expenses:
            story.append(Paragraph("<b>Materialen en Kosten:</b>", ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1F4E78'))))
            story.append(Spacer(1, 4))
            exp_table_content = [[Paragraph("<b>Document</b>", sub_style), Paragraph("<b>Dag</b>", sub_style), Paragraph("<b>Omschrijving</b>", sub_style), Paragraph("<b>Bedrag (€)</b>", sub_style)]]
            for ex in proj_expenses:
                d_nl = day_to_nl.get(ex["Gün"], ex["Gün"])
                d_str = f"{d_nl} ({ex['Tarih']})" if ex.get('Tarih') else d_nl
                exp_table_content.append([
                    Paragraph(f"<b>{ex['Kod']}</b>", sub_style),
                    Paragraph(d_str, sub_style),
                    Paragraph(ex["Açıklama"], sub_style),
                    Paragraph(f"€{ex['Tutar']:.2f}", sub_style)
                ])
                total_cost += ex["Tutar"]
            t_exp = Table(exp_table_content, colWidths=[80, 95, 260, 65])
            t_exp.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E9ECEF')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(t_exp)
            story.append(Spacer(1, 10))

        summary_text = f"<b>Totale uren:</b> {total_hours} uur<br/><b>Totale kosten:</b> €{total_cost:.2f}"
        t_summary = Table([[Paragraph(summary_text, sub_style), Paragraph("<b>Klantakkoord / Handtekening:</b><br/><br/>___________________", sub_style)]], colWidths=[270, 265])
        t_summary.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_summary)
        
        receipts_with_images = [ex for ex in proj_expenses if ex.get("Görsel_b64") is not None]
        if receipts_with_images:
            story.append(PageBreak())
            story.append(Paragraph("<b>Bonnetjes en Facturen (Documenten)</b>", ParagraphStyle('ReceiptTitle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#1F4E78'))))
            story.append(Spacer(1, 8))
            
            img_table_data = []
            row_cells = []
            
            for idx, ex in enumerate(receipts_with_images):
                try:
                    b64_data = ex.get("Görsel_b64")
                    if not b64_data:
                        continue
                    rec_io = io.BytesIO(base64.b64decode(b64_data))
                    pil_rec = PILImage.open(rec_io).convert("RGB")
                    draw = ImageDraw.Draw(pil_rec)
                    w_img, h_img = pil_rec.size
                    
                    banner_height = int(h_img * 0.09)
                    if banner_height < 25: banner_height = 25
                    draw.rectangle([(0, 0), (w_img, banner_height)], fill=(31, 78, 120))
                    
                    try:
                        font = ImageFont.truetype("arial.ttf", int(banner_height * 0.55))
                    except IOError:
                        font = ImageFont.load_default()
                        
                    d_nl = day_to_nl.get(ex["Gün"], ex["Gün"])
                    draw.text((10, banner_height * 0.2), f"{ex['Kod']} | {d_nl} | €{ex['Tutar']:.2f}", fill=(255, 255, 255), font=font)
                    
                    rec_io_processed = io.BytesIO()
                    pil_rec.save(rec_io_processed, format='JPEG')
                    rec_io_processed.seek(0)
                    
                    aspect = h_img / w_img
                    img_w = 220
                    img_h = img_w * aspect
                    if img_h > 210:
                        img_h = 210
                        img_w = img_h / aspect
                        
                    rl_rec_img = RLImage(rec_io_processed, width=img_w, height=img_h)
                    
                    cell_content = [
                        Paragraph(f"<b>{ex['Kod']}</b> - {d_nl} - {ex['Açıklama']} (€{ex['Tutar']:.2f})", sub_style),
                        Spacer(1, 2),
                        rl_rec_img
                    ]
                    row_cells.append(cell_content)
                    
                    if len(row_cells) == 2:
                        img_table_data.append(row_cells)
                        row_cells = []
                except Exception:
                    pass
                    
            if row_cells:
                row_cells.append("")
                img_table_data.append(row_cells)
                
            if img_table_data:
                t_receipts = Table(img_table_data, colWidths=[260, 260])
                t_receipts.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ]))
                story.append(t_receipts)
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    # --- HAFTANIN EN ALTINDA TEK BİR "PDF OLUŞTUR" BÖLÜMÜ ---
    st.markdown("---")
    st.markdown("### 📄 Rapor Oluşturma Merkezi")
    
    if all_entries or all_expenses:
        if st.button("🚀 Bu Haftanın PDF Raporlarını Oluştur", type="primary", key=f"btn_create_pdfs_{week_no}"):
            st.session_state[f"pdf_generated_{week_no}"] = True
            st.success("Haftalık PDF raporları başarıyla oluşturuldu! Aşağıdan indirebilirsiniz.")
            st.rerun()
            
        if st.session_state.get(f"pdf_generated_{week_no}", False):
            st.write("**İndirilebilir Proje PDF Raporları:**")
            
            active_projects = set([e["Proje"] for e in all_entries] + [ex["Proje"] for ex in all_expenses])
            
            for proj in active_projects:
                proj_entries = [e for e in all_entries if e["Proje"] == proj]
                pdf_file = create_pdf(proj, proj_entries, all_expenses, week_no, sel_year)
                pdf_bytes = pdf_file.getvalue()
                pdf_filename = f"Werkbon_Week{week_no}_{sel_year}_{proj.replace(' ', '_').replace('(', '').replace(')', '')}.pdf"
                
                if pdf_filename not in st.session_state.pdf_archive:
                    st.session_state.pdf_archive[pdf_filename] = base64.b64encode(pdf_bytes).decode('utf-8')
                    db_save("pdf_archive", st.session_state.pdf_archive)
                
                col_dl1, col_dl2 = st.columns([3, 1])
                with col_dl1:
                    st.download_button(
                        label=f"📥 {proj} - PDF İndir (Week {week_no})",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"dl_btn_{proj}_{week_no}"
                    )
                with col_dl2:
                    if current_week_key in st.session_state.completed_weeks:
                        if st.button(f"🔄 Aktif Yap", key=f"unmark_{proj}_{week_no}"):
                            st.session_state.completed_weeks.remove(current_week_key)
                            db_save("completed_weeks", list(st.session_state.completed_weeks))
                            st.rerun()
                    else:
                        if st.button(f"✅ Tamamla", key=f"mark_{proj}_{week_no}"):
                            st.session_state.completed_weeks.add(current_week_key)
                            db_save("completed_weeks", list(st.session_state.completed_weeks))
                            st.rerun()
    else:
        st.info("Bu hafta için henüz çalışma kaydı veya gider fişi girilmedi. Veri girdiğinizde en altta PDF oluşturma butonu aktifleşecektir.")
