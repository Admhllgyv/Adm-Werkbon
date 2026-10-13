import streamlit as st
import pandas as pd
import json
import base64
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage
import psycopg2

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

# --- SUPABASE VERİTABANI BAĞLANTISI VE ÖNBELLEKLEME ---
@st.cache_resource
def get_db_connection_pool():
    try:
        if "connections" in st.secrets and "postgres" in st.secrets["connections"]:
            url = st.secrets["connections"]["postgres"]["url"]
        elif "postgres_url" in st.secrets:
            url = st.secrets["postgres_url"]
        else:
            url = "postgresql://postgres.iowaxfgqfehdentzyipq:sifreniz@aws-1-eu-west-1.pooler.supabase.co:5432/postgres"
        return url
    except Exception:
        return None

def get_db_connection():
    url = get_db_connection_pool()
    if url:
        try:
            return psycopg2.connect(url)
        except Exception:
            return None
    return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)''')
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            pass
    return False

db_active = init_db()

@st.cache_data(ttl=300)
def load_all_data():
    conn = get_db_connection()
    data = {}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM kv_store")
            rows = cur.fetchall()
            for k, v in rows:
                try:
                    data[k] = json.loads(v)
                except:
                    data[k] = v
            cur.close()
            conn.close()
        except Exception:
            pass
    return data

db_cache = load_all_data()

def db_save(key, data):
    val_str = json.dumps(data, ensure_ascii=False)
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, val_str)
            )
            conn.commit()
            cur.close()
            conn.close()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Kayıt Hatası ({key}): {e}")

def db_load(key, default_val):
    return db_cache.get(key, default_val)

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
    st.session_state.expense_categories = db_load("expense_categories", ["Malzeme", "Su borusu", "Şalter", "Parking", "Kabel", "Verlichting", "Eten", "Hotel"])

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

today = datetime.today()
current_iso_year, current_iso_week, _ = today.isocalendar()

# --- SEKME BÖLÜMLERİ (BAĞIMSIZ BÖLGELER) ---

tab_entry, tab_preview, tab_monthly, tab_projects, tab_archive, tab_settings = st.tabs([
    "📝 Werkbon", "📊 Özet", "📅 Aylık Rapor", "📁 Projeler", "📚 Arşiv", "⚙️ Ayarlar"
])

# 1. AYARLAR SEKMESİ (İZOLE)
@st.fragment
def render_settings_tab():
    st.header("⚙️ Ayarlar ve Bulut Veritabanı")
    if db_active:
        st.success("🟢 Bulut Veritabanı (Supabase/PostgreSQL) Aktif ve Hızlandırılmış Modda Çalışıyor!")
    else:
        st.error("🔴 Bulut Veritabanı Bağlantısı Kurulamadı!")

    st.markdown("---")
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
        cw[0].write(f"👷 {w}")
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

with tab_settings:
    render_settings_tab()

# 2. PROJELER SEKMESİ (İZOLE)
@st.fragment
def render_projects_tab():
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
            st.markdown("#### 📋 Projeye Ait Geçmiş Çalışma Kayıtları")
            proj_full_name = f"{prj['code']} - {prj['name']}"
            matched_entries = []
            matched_expenses = []

            for wk_k, wk_val in st.session_state.weekly_data.items():
                for entry in wk_val.get("entries", []):
                    if entry.get("Proje") == proj_full_name or prj['name'] in entry.get("Proje", "") or prj['code'] in entry.get("Proje", ""):
                        matched_entries.append({**entry, "Hafta": wk_k})
                for exp in wk_val.get("expenses", []):
                    if exp.get("Proje") == proj_full_name or prj['name'] in exp.get("Proje", "") or prj['code'] in exp.get("Proje", ""):
                        matched_expenses.append({**exp, "Hafta": wk_k})

            if matched_entries:
                df_proj = pd.DataFrame(matched_entries)
                st.markdown(f'<div class="table-container">{df_proj[["Hafta", "Gün", "Tarih", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            else:
                st.info("Bu projeye ait çalışma kaydı bulunmuyor.")

with tab_projects:
    render_projects_tab()

# 3. ARŞİV SEKMESİ (İZOLE)
@st.fragment
def render_archive_tab():
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

with tab_archive:
    render_archive_tab()

# 4. ÖZET SEKMESİ (İZOLE)
@st.fragment
def render_preview_tab():
    st.header("📊 Haftalık Özet, Saatler ve Fiş Detayları")

    col_py1, col_py2 = st.columns(2)
    with col_py1:
        prev_sel_year = st.slider("Yıl", 2026, 2035, current_iso_year, key="prev_y_slide")
    with col_py2:
        prev_week_no = st.slider("Hafta No", 1, 53, current_iso_week, key="prev_w_slide")

    wk_key = f"{prev_sel_year}-W{prev_week_no}"
    w_data = st.session_state.weekly_data.get(wk_key, {"entries": [], "expenses": []})

    if w_data["entries"] or w_data["expenses"]:
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

with tab_preview:
    render_preview_tab()

# 5. AYLIK RAPOR SEKMESİ (İZOLE)
@st.fragment
def render_monthly_tab():
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

    if monthly_entries:
        df_m = pd.DataFrame(monthly_entries)
        total_m_hours = df_m["Saat"].sum()

        st.markdown("---")
        st.metric(label=f"📌 {sel_month_name} {sel_month_year} Toplam Çalışma Saati", value=f"{total_m_hours} Saat")

        st.markdown("### 👷 Çalışan Bazlı Aylık Toplamlar")
        df_m_worker = df_m.groupby("Çalışan")["Saat"].sum().reset_index()
        st.markdown(f'<div class="table-container">{df_m_worker.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
    else:
        st.info(f"{sel_month_name} {sel_month_year} dönemi için kayıt bulunmuyor.")

with tab_monthly:
    render_monthly_tab()

# 6. WERKBON GİRİŞ SEKMESİ (TAMAMEN İZOLE VE ANLIK MİDARİ)
@st.fragment
def render_werkbon_entry_tab():
    st.markdown(f"### ⚡ {st.session_state.comp_name}")

    col_ey1, col_ey2 = st.columns(2)
    with col_ey1:
        sel_year = st.slider("Yıl Seçimi", 2026, 2035, current_iso_year, key="entry_y_slide")
    with col_ey2:
        week_no = st.slider("Hafta Seçimi", 1, 53, current_iso_week, key="entry_w_slide")

    current_week_key = f"{sel_year}-W{week_no}"
    is_week_locked = current_week_key in st.session_state.completed_weeks

    if is_week_locked:
        st.warning("🔴 Bu hafta tamamlandı olarak işaretlendi.")
    else:
        st.success("🟢 Hafta düzenlenebilir durumda.")

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
            num_projects = st.number_input(f"Günlük Proje Sayısı ({day})", min_value=0, max_value=5, key=num_proj_key, disabled=is_week_locked)

            if num_projects > 0:
                for p_i in range(int(num_projects)):
                    p_key = f"proj_sel_{day}{p_i}{week_no}"

                    default_proj = "Seçiniz"
                    if p_i < len(saved_projects_for_day) and saved_projects_for_day[p_i] in project_options:
                        default_proj = saved_projects_for_day[p_i]

                    if p_key not in st.session_state or st.session_state[p_key] not in project_options:
                        st.session_state[p_key] = default_proj

                    proj_sel = st.selectbox(f"Proje {p_i+1} ({day})", project_options, key=p_key, disabled=is_week_locked)

                    if proj_sel != "Seçiniz":
                        proj_entries = [e for e in day_entries if e.get("Proje") == proj_sel]
                        default_num_workers = max(len(proj_entries), 1 if proj_entries else 0)
                        num_w_key = f"num_w_{day}{p_i}{week_no}"
                        if num_w_key not in st.session_state:
                            st.session_state[num_w_key] = default_num_workers

                        num_workers = st.number_input(f"Çalışan Sayısı ({proj_sel} - {day})", min_value=0, max_value=5, key=num_w_key, disabled=is_week_locked)

                        for w_i in range(int(num_workers)):
                            w_key = f"w_slide_{day}{p_i}{w_i}{week_no}"
                            s_key = f"s_slide{day}{p_i}{w_i}{week_no}"
                            pk_key = f"p_slide{day}{p_i}{w_i}{week_no}"
                            e_key = f"e_slide{day}{p_i}{w_i}{week_no}"

                            saved_w_entry = proj_entries[w_i] if w_i < len(proj_entries) else None
                            default_worker = saved_w_entry.get("Çalışan", "Seçiniz") if saved_w_entry else "Seçiniz"

                            if w_key not in st.session_state:
                                st.session_state[w_key] = default_worker

                            wrk = st.selectbox(f"Çalışan {w_i+1}", worker_options, key=w_key, disabled=is_week_locked)

                            if wrk != "Seçiniz":
                                def_s = saved_w_entry.get("Başlangıç", "07:00") if saved_w_entry else "07:00"
                                def_p = saved_w_entry.get("Mola", "00:45") if saved_w_entry else "00:45"
                                def_e = saved_w_entry.get("Bitiş", "15:45") if saved_w_entry else "15:45"

                                final_start = st.select_slider(f"Başlangıç - {wrk}", options=start_slots, value=def_s, key=f"s_sl_{day}{p_i}{w_i}_{week_no}")
                                final_pause = st.select_slider(f"Mola - {wrk}", options=pause_slots, value=def_p, key=f"p_sl_{day}{p_i}{w_i}_{week_no}")
                                final_stop = st.select_slider(f"Bitiş - {wrk}", options=end_slots, value=def_e, key=f"e_sl_{day}{p_i}{w_i}_{week_no}")

                                calc_hours = calculate_net_hours(final_start, final_pause, final_stop)

                                all_entries.append({
                                    "Gün": day,
                                    "Tarih": day_date_str,
                                    "Proje": proj_sel,
                                    "Çalışan": wrk,
                                    "Başlangıç": final_start,
                                    "Mola": final_pause,
                                    "Bitiş": final_stop,
                                    "Saat": calc_hours
                                })

                        day_expenses = [ex for ex in saved_expenses_by_day.get(day, []) if ex.get("Proje") == proj_sel]
                        num_exp_key = f"num_exp_{day}{p_i}{week_no}"
                        if num_exp_key not in st.session_state:
                            st.session_state[num_exp_key] = len(day_expenses)

                        num_exp = st.number_input(f"Fiş Sayısı ({proj_sel})", min_value=0, max_value=5, key=num_exp_key, disabled=is_week_locked)

                        for j in range(int(num_exp)):
                            saved_exp = day_expenses[j] if j < len(day_expenses) else None
                            e_cols = st.columns([2, 1.5, 2])
                            with e_cols[0]:
                                exp_desc = st.selectbox("Gider", st.session_state.expense_categories, key=f"exp_desc_{day}{p_i}{j}{week_no}")
                            with e_cols[1]:
                                exp_amount = st.number_input("Tutar (€)", min_value=0.0, value=float(saved_exp.get("Tutar", 10.0)) if saved_exp else 10.0, key=f"exp_amt_{day}{p_i}{j}{week_no}")
                            with e_cols[2]:
                                exp_file = st.file_uploader("Fiş Görseli", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}{p_i}{j}_{week_no}")

                            exp_b64 = saved_exp.get("Görsel_b64", None) if saved_exp else None
                            if exp_file is not None:
                                exp_b64 = base64.b64encode(exp_file.getvalue()).decode('utf-8')

                            if exp_amount > 0:
                                all_expenses.append({
                                    "Gün": day,
                                    "Tarih": day_date_str,
                                    "Proje": proj_sel,
                                    "Kod": "",
                                    "Açıklama": exp_desc,
                                    "Tutar": exp_amount,
                                    "Görsel_b64": exp_b64
                                })

    # ANLIK GEÇİCİ HAFIZA GÜNCELLEMESİ (SAYFA YENİLENMEDEN)
    existing_week_data = st.session_state.weekly_data.get(current_week_key, {"entries": [], "expenses": []})
    final_entries = all_entries if all_entries else existing_week_data.get("entries", [])
    final_expenses = all_expenses if all_expenses else existing_week_data.get("expenses", [])

    st.session_state.weekly_data[current_week_key] = {"entries": final_entries, "expenses": final_expenses}

    st.markdown("---")
    if st.button("💾 Tüm Değişiklikleri Veritabanına Kaydet", type="primary"):
        db_save("weekly_data", st.session_state.weekly_data)
        st.success("Tüm veriler Supabase veritabanına kaydedildi!")

with tab_entry:
    render_werkbon_entry_tab()
