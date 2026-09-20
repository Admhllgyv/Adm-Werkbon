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

st.set_page_config(page_title="ADM Technics - Werkbon Automatisering", layout="wide")

AUTO_BACKUP_FILE = "auto_backup.json"

# --- VERITABANI VE OTOMATIK YEDEKLEME BASLANGIC ISLEMLERI (AYNEN KORUNDU) ---
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

# --- UYGULAMA ACILIRKEN OTOMATIK GERI YUKLEME KONTROLU ---
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

# Sekmeler (Flamanca)
tab_entry, tab_preview, tab_projects, tab_archive, tab_settings = st.tabs([
    "📝 Werkbon", "📊 Overzicht", "📁 Projecten", "📚 Archief", "⚙️ Instellingen"
])

with tab_settings:
    st.header("⚙️ Instellingen & Automatische Beveiliging")
    
    st.subheader("Bedrijfsgegevens")
    logo_io = get_logo_io()
    if logo_io is not None:
        st.image(logo_io, width=70, caption="Huidig Logo")
        
    uploaded_logo = st.file_uploader("Logo Wijzigen (PNG / JPG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        try:
            b64_str = base64.b64encode(uploaded_logo.getvalue()).decode('utf-8')
            st.session_state.comp_logo_b64 = b64_str
            db_save("comp_logo_b64", b64_str)
            st.success("Logo bijgewerkt!")
            st.rerun()
        except Exception as e:
            st.error(f"Fout: {e}")

    new_comp_name = st.text_input("Bedrijfsnaam", value=st.session_state.comp_name)
    if new_comp_name != st.session_state.comp_name:
        st.session_state.comp_name = new_comp_name
        db_save("comp_name", new_comp_name)

    new_comp_address = st.text_input("Bedrijfsadres", value=st.session_state.comp_address)
    if new_comp_address != st.session_state.comp_address:
        st.session_state.comp_address = new_comp_address
        db_save("comp_address", new_comp_address)

    new_comp_btw = st.text_input("BTW-nummer", value=st.session_state.comp_btw)
    if new_comp_btw != st.session_state.comp_btw:
        st.session_state.comp_btw = new_comp_btw
        db_save("comp_btw", new_comp_btw)

    st.markdown("---")
    st.subheader("Medewerkers")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        new_w = st.text_input("Naam nieuwe medewerker", label_visibility="collapsed")
    with col_w2:
        if st.button("Medewerker Toevoegen"):
            if new_w and new_w not in st.session_state.workers:
                st.session_state.workers.append(new_w)
                db_save("workers", st.session_state.workers)
                st.rerun()
    for w in st.session_state.workers:
        cw = st.columns([3, 1])
        cw[0].write(f"- {w}")
        if len(st.session_state.workers) > 1 and cw[1].button("Verwijderen", key=f"del_w_{w}"):
            st.session_state.workers.remove(w)
            db_save("workers", st.session_state.workers)
            st.rerun()

    st.markdown("---")
    st.subheader("Onkosten- / Materiaalrubrieken")
    col_ex1, col_ex2 = st.columns([2, 1])
    with col_ex1:
        new_exp_cat = st.text_input("Nieuwe onkosten-/materiaalsoort", label_visibility="collapsed")
    with col_ex2:
        if st.button("Rubriek Toevoegen"):
            if new_exp_cat and new_exp_cat not in st.session_state.expense_categories:
                st.session_state.expense_categories.append(new_exp_cat)
                db_save("expense_categories", st.session_state.expense_categories)
                st.rerun()
    for cat in st.session_state.expense_categories:
        cc = st.columns([3, 1])
        cc[0].write(f"- {cat}")
        if len(st.session_state.expense_categories) > 1 and cc[1].button("Verwijderen", key=f"del_cat_{cat}"):
            st.session_state.expense_categories.remove(cat)
            db_save("expense_categories", st.session_state.expense_categories)
            st.rerun()

    st.markdown("---")
    st.subheader("💾 Gegevensback-up & Excel-rapport")
    
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            all_flat_entries = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for entry in wk_val.get("entries", []):
                    all_flat_entries.append({"Week": wk_k, **entry})
            if all_flat_entries:
                pd.DataFrame(all_flat_entries).to_excel(writer, sheet_name='Werk_Registraties', index=False)
            
            all_flat_expenses = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for exp in wk_val.get("expenses", []):
                    exp_copy = exp.copy()
                    exp_copy.pop("Görsel_b64", None)
                    all_flat_expenses.append({"Week": wk_k, **exp_copy})
            if all_flat_expenses:
                pd.DataFrame(all_flat_expenses).to_excel(writer, sheet_name='Onkosten_Bonnen', index=False)
                
            if st.session_state.projects:
                pd.DataFrame(st.session_state.projects).to_excel(writer, sheet_name='Projecten', index=False)
                
            if st.session_state.workers:
                pd.DataFrame({"Medewerkers": st.session_state.workers}).to_excel(writer, sheet_name='Medewerkers', index=False)
        excel_data = excel_buffer.getvalue()
        
        st.download_button(
            label="📊 Download Alle Gegevens als Excel (.xlsx)",
            data=excel_data,
            file_name=f"adm_technics_rapport_{datetime.now().strftime('%Y%m%d')}.xlsx",
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
        label="📥 Maak Back-up van Alle Gegevens (JSON)",
        data=json_str,
        file_name=f"adm_technics_backup_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

    uploaded_backup = st.file_uploader("📂 Back-up Herstellen", type=["json"])
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
            st.success("Back-up succesvol hersteld!")
            st.rerun()
        except Exception as e:
            st.error(f"Fout: {e}")

with tab_projects:
    st.header("📁 Projectbeheer & Historische Gegevens")
    with st.form("add_project_form"):
        p_name = st.text_input("Project- / Klantnaam")
        p_code = st.text_input("Projectnummer / Code (Bijv: E260003)")
        if st.form_submit_button("Project Opslaan") and p_name:
            st.session_state.projects.append({"name": p_name, "code": p_code if p_code else "E260000"})
            db_save("projects", st.session_state.projects)
            st.success("Project toegevoegd!")
            st.rerun()
            
    for idx, prj in enumerate(st.session_state.projects):
        with st.expander(f"📌 {prj['code']} - {prj['name']}"):
            upd_name = st.text_input("Naam", value=prj['name'], key=f"upd_n_{idx}")
            upd_code = st.text_input("Code", value=prj['code'], key=f"upd_c_{idx}")
            
            pcol1, pcol2 = st.columns([1, 1])
            with pcol1:
                if st.button("Bijwerken", key=f"up_p_{idx}"):
                    prj['name'] = upd_name
                    prj['code'] = upd_code
                    db_save("projects", st.session_state.projects)
                    st.success("Bijgewerkt!")
                    st.rerun()
            with pcol2:
                if st.button("🗑️ Project Verwijderen", key=f"del_p_{idx}"):
                    st.session_state.projects.pop(idx)
                    db_save("projects", st.session_state.projects)
                    st.success("Project verwijderd!")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("#### 📋 Historische Registraties van dit Project")
            proj_full_name = f"{prj['code']} - {prj['name']}"
            matched_entries = []
            for wk_k, wk_val in st.session_state.weekly_data.items():
                for entry in wk_val.get("entries", []):
                    if entry.get("Proje") == proj_full_name or prj['name'] in entry.get("Proje", "") or prj['code'] in entry.get("Proje", ""):
                        matched_entries.append({**entry, "Week": wk_k})
            
            if matched_entries:
                df_proj = pd.DataFrame(matched_entries)
                st.markdown(f'<div class="table-container">{df_proj[["Week", "Gün", "Tarih", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            else:
                st.info("Geen registraties gevonden voor dit project.")

with tab_archive:
    st.header("📚 PDF-archief")
    if st.session_state.pdf_archive:
        for filename, b64_pdf in list(st.session_state.pdf_archive.items()):
            col_ar1, col_ar2, col_ar3 = st.columns([3, 1, 1])
            with col_ar1:
                st.write(f"📄 {filename}")
            with col_ar2:
                try:
                    st.download_button("📥 Download", data=base64.b64decode(b64_pdf), file_name=filename, mime="application/pdf", key=f"arch_dl_{filename}")
                except Exception:
                    pass
            with col_ar3:
                if st.button("🗑️ Verwijderen", key=f"arch_del_{filename}"):
                    del st.session_state.pdf_archive[filename]
                    db_save("pdf_archive", st.session_state.pdf_archive)
                    st.rerun()
    else:
        st.info("Het archief is leeg.")

today = datetime.today()
current_iso_year, current_iso_week, _ = today.isocalendar()

with tab_preview:
    st.header("📊 Wekelijks Overzicht & Gedetailleerde Analyse")
    
    col_py1, col_py2 = st.columns(2)
    with col_py1:
        prev_sel_year = st.slider("Jaar", 2026, 2035, current_iso_year, key="prev_y_slide")
    with col_py2:
        prev_week_no = st.slider("Weeknummer", 1, 53, current_iso_week, key="prev_w_slide")
        
    wk_key = f"{prev_sel_year}-W{prev_week_no}"
    w_data = st.session_state.weekly_data.get(wk_key, {"entries": [], "expenses": []})
    
    if w_data["entries"]:
        df_p = pd.DataFrame(w_data["entries"])
        
        st.markdown("### 📋 Alle Werkregistraties")
        st.markdown(f'<div class="table-container">{df_p[["Gün", "Tarih", "Proje", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]].to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        col_sum1, col_sum2 = st.columns(2)
        
        with col_sum1:
            st.markdown("#### 👷 Uren per Medewerker")
            df_worker = df_p.groupby("Çalışan")["Saat"].sum().reset_index()
            st.markdown(f'<div class="table-container">{df_worker.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            
        with col_sum2:
            st.markdown("#### 📁 Uren per Project")
            df_proj_sum = df_p.groupby("Proje")["Saat"].sum().reset_index()
            st.markdown(f'<div class="table-container">{df_proj_sum.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
            
        st.markdown("---")
        st.markdown("#### 🔍 Project- & Medewerkermatrix (Wie heeft hoeveel uur gewerkt per project?)")
        df_pivot = df_p.pivot_table(index="Proje", columns="Çalışan", values="Saat", aggfunc="sum", fill_value=0).reset_index()
        st.markdown(f'<div class="table-container">{df_pivot.to_html(index=False, classes="resp-table")}</div>', unsafe_allow_html=True)
        
    else:
        st.info("Geen registraties gevonden voor deze week.")

with tab_entry:
    st.markdown(f"### ⚡ {st.session_state.comp_name}")
    
    col_ey1, col_ey2 = st.columns(2)
    with col_ey1:
        sel_year = st.slider("Jaar Selecteren", 2026, 2035, current_iso_year, key="entry_y_slide")
    with col_ey2:
        week_no = st.slider("Week Selecteren", 1, 53, current_iso_week, key="entry_w_slide")
    
    current_week_key = f"{sel_year}-W{week_no}"
    if current_week_key in st.session_state.completed_weeks:
        st.caption("🔴 Deze week is gemarkeerd als voltooid.")

    st.markdown("---")

    sorted_projects = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    project_options = ["Selecteer"] + [f"{p['code']} - {p['name']}" for p in sorted_projects]
    worker_options = ["Selecteer"] + st.session_state.workers

    saved_week_data = st.session_state.weekly_data.get(current_week_key, {"entries": [], "expenses": []})
    
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []
    exp_counter = 1

    for day_idx, day in enumerate(days):
        day_date_str = get_date_for_day(sel_year, week_no, day_idx)
        d_nl_name = day_to_nl[day]
        expand_label = f"📌 {d_nl_name} ({day}) - {day_date_str}"
        
        with st.expander(expand_label, expanded=False):
            num_projects = st.number_input(f"Aantal projecten / taken ({d_nl_name})", min_value=0, max_value=5, value=0, key=f"num_proj_{day}_{week_no}")
            
            if num_projects > 0:
                st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 12px 0;'>", unsafe_allow_html=True)

            for p_i in range(int(num_projects)):
                if p_i > 0:
                    st.markdown("<hr style='border: 1px solid #CBD5E1; margin: 16px 0;'>", unsafe_allow_html=True)

                p_key = f"proj_sel_{day}_{p_i}_{week_no}"
                if p_key not in st.session_state:
                    st.session_state[p_key] = "Selecteer"
                
                cur_proj = st.session_state.get(p_key, "Selecteer")
                if cur_proj not in project_options:
                    cur_proj = "Selecteer"
                p_idx = project_options.index(cur_proj)
                
                proj_sel = st.selectbox(f"Project {p_i+1} ({d_nl_name})", project_options, index=p_idx, key=p_key)

                if proj_sel != "Selecteer":
                    st.markdown(f"#### 📁 {proj_sel}")
                    
                    num_workers = st.number_input(f"Aantal medewerkers ({proj_sel} - {d_nl_name})", min_value=0, max_value=5, value=0, key=f"num_w_{day}_{p_i}_{week_no}")
                    
                    for w_i in range(int(num_workers)):
                        if w_i > 0:
                            st.markdown("<hr style='border: 1px dashed #CBD5E1; margin: 8px 0;'>", unsafe_allow_html=True)
                            
                        w_key = f"w_slide_{day}_{p_i}_{w_i}_{week_no}"
                        s_key = f"s_slide_{day}_{p_i}_{w_i}_{week_no}"
                        pk_key = f"p_slide_{day}_{p_i}_{w_i}_{week_no}"
                        e_key = f"e_slide_{day}_{p_i}_{w_i}_{week_no}"
                        prev_w_key = f"prev_w_{day}_{p_i}_{w_i}_{week_no}"

                        if w_key not in st.session_state:
                            st.session_state[w_key] = "Selecteer"
                        
                        cur_worker = st.session_state.get(w_key, "Selecteer")
                        if cur_worker not in worker_options:
                            cur_worker = "Selecteer"
                        w_idx = worker_options.index(cur_worker)

                        wrk = st.selectbox(f"Medewerker {w_i+1} ({proj_sel})", worker_options, index=w_idx, key=w_key)

                        if wrk == "Adem":
                            def_s, def_p, def_e = "05:30", "01:45", "17:15"
                        else:
                            def_s, def_p, def_e = "07:00", "00:45", "15:45"

                        prev_wrk = st.session_state.get(prev_w_key, "Selecteer")
                        if s_key not in st.session_state or prev_wrk != wrk:
                            st.session_state[s_key] = def_s
                            st.session_state[pk_key] = def_p
                            st.session_state[e_key] = def_e
                            st.session_state[prev_w_key] = wrk

                        if wrk != "Selecteer":
                            st.markdown(f"⏱️ **Tijden - {wrk}**")

                            col_s1, col_s2 = st.columns([3, 1])
                            with col_s1:
                                st.markdown(f"**Starttijd**")
                            with col_s2:
                                man_s = st.checkbox("Handmatig", key=f"man_s_{day}_{p_i}_{w_i}_{week_no}")
                            
                            if man_s:
                                final_start = st.text_input("Handmatige starttijd", value=st.session_state.get(s_key, def_s), key=f"s_man_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed")
                            else:
                                curr_s = st.session_state.get(s_key, def_s)
                                if curr_s not in start_slots:
                                    curr_s = start_slots[0]
                                final_start = st.select_slider(
                                    f"Starttijd {w_i+1}", options=start_slots, value=curr_s, key=f"s_sl_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed"
                                )
                                st.session_state[s_key] = final_start

                            col_p1, col_p2 = st.columns([3, 1])
                            with col_p1:
                                st.markdown(f"**Pauze**")
                            with col_p2:
                                man_p = st.checkbox("Handmatig", key=f"man_p_{day}_{p_i}_{w_i}_{week_no}")

                            if man_p:
                                final_pause = st.text_input("Handmatige pauze", value=st.session_state.get(pk_key, def_p), key=f"p_man_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed")
                            else:
                                curr_p = st.session_state.get(pk_key, def_p)
                                if curr_p not in pause_slots:
                                    curr_p = pause_slots[0]
                                final_pause = st.select_slider(
                                    f"Pauze {w_i+1}", options=pause_slots, value=curr_p, key=f"p_sl_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed"
                                )
                                st.session_state[pk_key] = final_pause

                            col_e1, col_e2 = st.columns([3, 1])
                            with col_e1:
                                st.markdown(f"**Eindtijd**")
                            with col_e2:
                                man_e = st.checkbox("Handmatig", key=f"man_e_{day}_{p_i}_{w_i}_{week_no}")

                            if man_e:
                                final_stop = st.text_input("Handmatige eindtijd", value=st.session_state.get(e_key, def_e), key=f"e_man_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed")
                            else:
                                curr_e = st.session_state.get(e_key, def_e)
                                if curr_e not in end_slots:
                                    curr_e = end_slots[0]
                                final_stop = st.select_slider(
                                    f"Eindtijd {w_i+1}", options=end_slots, value=curr_e, key=f"e_sl_{day}_{p_i}_{w_i}_{week_no}", label_visibility="collapsed"
                                )
                                st.session_state[e_key] = final_stop
                            
                            calc_hours = calculate_net_hours(final_start, final_pause, final_stop)
                            st.markdown(f"⏱️ **{wrk}** | Netto: **<span style='color:blue'>{calc_hours} uur</span>** ({final_start} - {final_stop}, Pauze: {final_pause})", unsafe_allow_html=True)

                            all_entries.append({
                                "Gün": d_nl_name,
                                "Tarih": day_date_str,
                                "Proje": proj_sel,
                                "Çalışan": wrk,
                                "Başlangıç": final_start,
                                "Mola": final_pause,
                                "Bitiş": final_stop,
                                "Saat": calc_hours
                            })
                        else:
                            st.info("Selecteerstublieft een medewerker.")

                    st.markdown(f"💶 **Bon / Onkosten ({proj_sel})**")
                    num_exp = st.number_input(f"Aantal bonnen ({proj_sel})", min_value=0, max_value=5, value=0, key=f"num_exp_{day}_{p_i}_{week_no}")
                    for j in range(int(num_exp)):
                        e_cols = st.columns([2, 1.5, 2.5])
                        with e_cols[0]:
                            exp_desc = st.selectbox("Rubriek", st.session_state.expense_categories, key=f"exp_desc_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        with e_cols[1]:
                            exp_amount = st.number_input("Bedrag", min_value=0.0, value=10.0, step=1.0, key=f"exp_amt_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        with e_cols[2]:
                            exp_file = st.file_uploader("Bon Uploaden", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{p_i}_{j}_{week_no}", label_visibility="collapsed")
                        
                        exp_b64 = None
                        if exp_file is not None:
                            try:
                                exp_b64 = base64.b64encode(exp_file.getvalue()).decode('utf-8')
                            except Exception:
                                pass

                        if exp_amount > 0:
                            all_expenses.append({
                                "Gün": d_nl_name,
                                "Tarih": day_date_str,
                                "Proje": proj_sel,
                                "Kod": f"Doc {exp_counter}",
                                "Açıklama": exp_desc,
                                "Tutar": exp_amount,
                                "Görsel_b64": exp_b64
                            })
                            exp_counter += 1
                else:
                    st.info("Selecteerstublieft eerst een project.")

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
        
        day_order = {"Maandag": 1, "Dinsdag": 2, "Woensdag": 3, "Donderdag": 4, "Vrijdag": 5, "Zaterdag": 6, "Zondag": 7}
        proj_entries = [e for e in entries if e["Proje"] == project_name]
        sorted_entries = sorted(proj_entries, key=lambda x: (x.get("Çalışan", ""), day_order.get(x.get("Gün", ""), 8)))

        table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                          for h in ["Medewerker", "Dag", "Start", "Pauze", "Einde", "Uren"]]]
        
        total_hours = 0
        worker_hours = {}
        for e in sorted_entries:
            d_str = f"{e['Gün']} ({e['Tarih']})" if e.get('Tarih') else e['Gün']
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
                d_str = f"{ex['Gün']} ({ex['Tarih']})" if ex.get('Tarih') else ex['Gün']
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
        
        # --- AKILLI GÖRSEL YERLEŞTİRME (FİŞLER 4'LÜ GRID, A4 BELGELER TAM SAYFA) ---
        receipts_with_img = []
        docs_with_img = []
        for ex in proj_expenses:
            if ex.get("Görsel_b64"):
                try:
                    img_bytes = base64.b64decode(ex["Görsel_b64"])
                    pil_img = PILImage.open(io.BytesIO(img_bytes))
                    orig_w, orig_h = pil_img.size
                    aspect = orig_h / orig_w
                    # Fiş/dekont dik ve dardır (aspect > 1.5), A4 belgeler daha dengelidir.
                    if aspect > 1.5:
                        receipts_with_img.append((ex, pil_img))
                    else:
                        docs_with_img.append((ex, pil_img))
                except Exception:
                    pass

        if receipts_with_img or docs_with_img:
            story.append(PageBreak())
            story.append(Paragraph("<b>Bijlagen / Bonnetjes en Documenten:</b>", ParagraphStyle('ImgHeader', fontName='Helvetica-Bold', fontSize=10, textColor=primary_color)))
            story.append(Spacer(1, 10))

            # A4 belgeler her biri 1 tam sayfaya
            for ex, pil_img in docs_with_img:
                story.append(Paragraph(f"<b>{ex['Kod']}</b> - {ex['Açıklama']} (€{ex['Tutar']:.2f}) - {ex['Gün']}", bold_sub_style))
                story.append(Spacer(1, 4))
                
                orig_w, orig_h = pil_img.size
                max_w, max_h = 450, 600
                aspect = orig_h / orig_w
                w = max_w
                h = max_w * aspect
                if h > max_h:
                    h = max_h
                    w = max_h / aspect
                    
                img_io = io.BytesIO()
                pil_img.save(img_io, format='JPEG', quality=90)
                img_io.seek(0)
                story.append(RLImage(img_io, width=w, height=h))
                story.append(PageBreak())

            # Fişler 4'lü gruplar halinde (2x2 Grid) tek sayfaya sığdırılır
            for i in range(0, len(receipts_with_img), 4):
                chunk = receipts_with_img[i:i+4]
                row1 = []
                row2 = []
                
                for idx, (ex, pil_img) in enumerate(chunk):
                    orig_w, orig_h = pil_img.size
                    max_w, max_h = 220, 240
                    aspect = orig_h / orig_w
                    w = max_w
                    h = max_w * aspect
                    if h > max_h:
                        h = max_h
                        w = max_h / aspect

                    img_io = io.BytesIO()
                    pil_img.save(img_io, format='JPEG', quality=90)
                    img_io.seek(0)
                    rl_img = RLImage(img_io, width=w, height=h)
                    
                    cell_content = [
                        Paragraph(f"<b>{ex['Kod']}</b> - {ex['Açıklama']} (€{ex['Tutar']:.2f})<br/>{ex['Gün']}", sub_style),
                        Spacer(1, 3),
                        rl_img
                    ]
                    if idx < 2:
                        row1.append(cell_content)
                    else:
                        row2.append(cell_content)
                
                while len(row1) < 2:
                    row1.append([Paragraph("", sub_style)])
                while len(row2) < 2 and len(chunk) > 2:
                    row2.append([Paragraph("", sub_style)])

                table_rows = [row1]
                if row2:
                    table_rows.append(row2)
                    
                t_grid = Table(table_rows, colWidths=[265, 265])
                t_grid.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, border_color),
                    ('BACKGROUND', (0,0), (-1,-1), light_bg),
                    ('PADDING', (0,0), (-1,-1), 6),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ]))
                story.append(t_grid)
                story.append(Spacer(1, 15))
                if i + 4 < len(receipts_with_img):
                    story.append(PageBreak())

        doc.build(story)
        buffer.seek(0)
        return buffer

    st.markdown("---")
    st.markdown("### 📄 PDF-Rapport Genereren")
    
    if all_entries or all_expenses:
        if st.button("🚀 PDF-Rapporten Genereren", type="primary", key=f"btn_pdf_{week_no}"):
            st.success("PDF-rapporten succesvol gegenereerd en toegevoegd aan het archief!")
            st.rerun()
            
        active_projects = set([e["Proje"] for e in all_entries] + [ex["Proje"] for ex in all_expenses])
        if active_projects:
            for proj in active_projects:
                p_entries = [e for e in all_entries if e["Proje"] == proj]
                pdf_file = create_pdf(proj, all_entries, all_expenses, week_no, sel_year)
                pdf_bytes = pdf_file.getvalue()
                pdf_filename = f"Werkbon_Week{week_no}_{sel_year}_{proj.replace(' ', '_').replace('(', '').replace(')', '')}.pdf"
                
                st.session_state.pdf_archive[pdf_filename] = base64.b64encode(pdf_bytes).decode('utf-8')
                db_save("pdf_archive", st.session_state.pdf_archive)
                
                col_dl1, col_dl2 = st.columns([3, 1])
                with col_dl1:
                    st.download_button(
                        label=f"📥 {proj} - Downloaden (Week {week_no})",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"dl_{proj}_{week_no}"
                    )
                with col_dl2:
                    if current_week_key in st.session_state.completed_weeks:
                        if st.button("🔄 Openen", key=f"unmark_{proj}_{week_no}"):
                            st.session_state.completed_weeks.remove(current_week_key)
                            db_save("completed_weeks", list(st.session_state.completed_weeks))
                            st.rerun()
                    else:
                        if st.button("✅ Voltooien", key=f"mark_{proj}_{week_no}"):
                            st.session_state.completed_weeks.add(current_week_key)
                            db_save("completed_weeks", list(st.session_state.completed_weeks))
                            st.rerun()
    else:
        st.info("Geen registraties ingevoerd voor deze week.")
