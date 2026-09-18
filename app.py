import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage, ImageDraw, ImageFont
from datetime import datetime, timedelta

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

# Samsung S23 Ultra & Mobile Optimized Compact CSS + Sekmeleri Aşağı İndirme
st.markdown("""
    <style>
    /* Sekmelerin üstteki tarayıcı çubuğu altında kalmaması ve aşağı inmesi için üst boşluk */
    .stTabs {
        margin-top: 25px !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 8px;
        padding-top: 10px;
    }
    .block-container {
        padding-left: 0.8rem;
        padding-right: 1.8rem; /* Sağ elde kaydırma / yanlış dokunma önleme payı */
        padding-top: 1.5rem;
        max-width: 100%;
    }
    /* Genel font küçültme ve kompakt görünüm */
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
    /* Günlük expander kutularına kalın ve belirgin kenarlık */
    .streamlit-expanderHeader {
        border: 2px solid #1F4E78 !important;
        border-radius: 6px !important;
        background-color: #F8F9FA !important;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'comp_name' not in st.session_state:
    st.session_state.comp_name = "ADM TECHNICS"
if 'comp_address' not in st.session_state:
    st.session_state.comp_address = "Schutveststraat 5, 3500 Diepenbeek"
if 'comp_btw' not in st.session_state:
    st.session_state.comp_btw = "BE0787743276"
if 'comp_logo' not in st.session_state:
    st.session_state.comp_logo = None
if 'workers' not in st.session_state:
    st.session_state.workers = ["Adem", "Melih"]

# Projeler Listesi (Proje Adı ve E serisi Kodlar)
if 'projects' not in st.session_state:
    st.session_state.projects = [
        {"name": "Kruidvat Diepenbeek", "code": "E260001"},
        {"name": "ICI PARIS XL Hasselt", "code": "E260002"}
    ]

# Gider Kategorileri
if 'expense_categories' not in st.session_state:
    st.session_state.expense_categories = ["Malzeme", "Su borusu", "Şalter", "Parking", "Kabel", "Verlichting"]

if 'weekly_data' not in st.session_state:
    st.session_state.weekly_data = {}
if 'completed_weeks' not in st.session_state:
    st.session_state.completed_weeks = set()

# Gün Türkçe -> Hollandaca Çeviri Sözlüğü
day_to_nl = {
    "Pazartesi": "Maandag",
    "Salı": "Dinsdag",
    "Çarşamba": "Woensdag",
    "Perşembe": "Donderdag",
    "Cuma": "Vrijdag",
    "Cumartesi": "Zaterdag",
    "Zondag": "Zondag"
}

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

tab_entry, tab_projects, tab_preview, tab_settings = st.tabs(["📝 Werkbon Girişi", "📁 Proje Yönetimi", "👀 Önizleme", "⚙️ Ayarlar"])

with tab_settings:
    st.header("⚙️ Firma, Çalışan ve Gider Ayarları")
    st.subheader("Firma Bilgileri ve Logo")
    st.session_state.comp_name = st.text_input("Firma Adı", value=st.session_state.comp_name)
    st.session_state.comp_address = st.text_input("Firma Adresi", value=st.session_state.comp_address)
    st.session_state.comp_btw = st.text_input("BTW Numarası", value=st.session_state.comp_btw)
    
    uploaded_logo = st.file_uploader("Firma Logosu Yükle (JPG / PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        st.session_state.comp_logo = uploaded_logo
        st.success("Logo güncellendi!")
    
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
                st.rerun()
    for w in st.session_state.workers:
        cw = st.columns([3, 1])
        cw[0].write(f"- {w}")
        if len(st.session_state.workers) > 1 and cw[1].button("Sil", key=f"del_w_{w}"):
            st.session_state.workers.remove(w)
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
                st.rerun()
    for ec in st.session_state.expense_categories:
        cec = st.columns([3, 1])
        cec[0].write(f"- {ec}")
        if len(st.session_state.expense_categories) > 1 and cec[1].button("Sil", key=f"del_ec_{ec}"):
            st.session_state.expense_categories.remove(ec)
            st.rerun()

with tab_projects:
    st.header("📁 Proje Yönetimi ve Arşiv")
    st.markdown("Önceden proje tanımlayarak günlük girişlerde hızlıca seçebilir ve ilgili projenin geçmiş dosyalarına ulaşabilirsiniz.")
    
    with st.form("add_project_form"):
        p_name = st.text_input("Proje / Müşteri Adı")
        p_code = st.text_input("Proje Numarası / Kodu (Örn: E260003)")
        submitted = st.form_submit_button("Yeni Proje Kaydet")
        if submitted and p_name:
            st.session_state.projects.append({"name": p_name, "code": p_code if p_code else "E260000"})
            st.success(f"'{p_name}' başarıyla eklendi!")
            st.rerun()
            
    st.subheader("Mevcut Projeler (Proje Koduna Göre Sıralı)")
    # Projeleri proj koduna göre azalan (en yeni en üstte) şekilde sıralıyoruz
    sorted_projects = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    
    for prj in sorted_projects:
        with st.expander(f"📌 {prj['code']} - {prj['name']}"):
            st.write(f"**Proje Kodu:** {prj['code']}")
            st.write("**Bu projeye ait geçmiş evrak ve fişler:**")
            found_docs = False
            for wk, w_data in st.session_state.weekly_data.items():
                for ex in w_data.get("expenses", []):
                    if prj['name'] in ex["Proje"] or prj['code'] in ex["Proje"]:
                        found_docs = True
                        st.text(f"• [Hafta {wk}] {ex['Kod']} - {ex['Açıklama']} (€{ex['Tutar']})")
                        if ex["Görsel"]:
                            st.image(ex["Görsel"], width=150)
            if not found_docs:
                st.info("Bu projeye ait henüz yüklenmiş bir gider/fiş bulunmuyor.")

with tab_entry:
    st.markdown(f"### ⚡ ADM Technics Werkbon")
    
    col_yr, col_wk = st.columns(2)
    with col_yr:
        sel_year = st.selectbox("Yıl", list(range(2026, 2036)), index=0)
    with col_wk:
        week_options = list(range(1, 54))
        formatted_week_options = []
        for w in week_options:
            w_key = f"{sel_year}-W{w}"
            status = "🔴 [Tamamlandı]" if w_key in st.session_state.completed_weeks else f"Week {w}"
            formatted_week_options.append((w, status))
        
        selected_week_tuple = st.selectbox(
            "Hafta Seçimi (Weeknummer)", 
            options=formatted_week_options, 
            format_func=lambda x: f"{x[1]} ({sel_year})" if "Tamamlandı" in x[1] else f"Week {x[0]} ({sel_year})",
            index=34
        )
        week_no = selected_week_tuple[0]
        current_week_key = f"{sel_year}-W{week_no}"

    st.markdown("---")

    # Proje seçenekleri kod sırasına göre sıralı (E260001, E260002 şeklinde)
    sorted_projects_dropdown = sorted(st.session_state.projects, key=lambda x: x['code'], reverse=True)
    project_options = [f"{p['code']} - {p['name']}" for p in sorted_projects_dropdown]
    if not project_options:
        project_options = ["E260000 - Genel Proje"]

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []
    exp_counter = 1

    for day in days:
        with st.expander(f"📌 {day} ({day_to_nl[day]})", expanded=(day == "Pazartesi")):
            num_rows = st.number_input(f"{day} çalışma satırı sayısı", min_value=1, max_value=10, value=1, key=f"num_{day}_{week_no}")
            for i in range(int(num_rows)):
                cols = st.columns([2, 1.5, 1.2, 1.2, 1.2])
                with cols[0]:
                    proj = st.selectbox("Proje Seç", project_options, key=f"p_{day}_{i}_{week_no}")
                with cols[1]:
                    wrk = st.selectbox("Çalışan", st.session_state.workers, key=f"w_{day}_{i}_{week_no}")
                with cols[2]:
                    s_choice = st.selectbox("Başlangıç", start_slots, index=13, key=f"s_choice_{day}_{i}_{week_no}")
                    start = st.text_input("Örn: 07:00", value="07:00", key=f"s_man_{day}_{i}_{week_no}") if s_choice == "Manuel Giriş" else s_choice
                with cols[3]:
                    p_choice = st.selectbox("Mola", pause_slots, index=2, key=f"p_choice_{day}_{i}_{week_no}")
                    pause = st.text_input("Örn: 00:45", value="00:45", key=f"p_man_{day}_{i}_{week_no}") if p_choice == "Manuel Giriş" else p_choice
                with cols[4]:
                    e_choice = st.selectbox("Bitiş", end_slots, index=15, key=f"e_choice_{day}_{i}_{week_no}")
                    stop = st.text_input("Örn: 15:45", value="15:45", key=f"e_man_{day}_{i}_{week_no}") if e_choice == "Manuel Giriş" else e_choice
                
                calculated_hours = calculate_net_hours(start, pause, stop)
                st.caption(f"⏱️ Net: **{calculated_hours} saat** ({start} - {stop}, Mola: {pause})")

                if proj:
                    all_entries.append({
                        "Gün": day,
                        "Proje": proj,
                        "Çalışan": wrk,
                        "Başlangıç": start,
                        "Mola": pause,
                        "Bitiş": stop,
                        "Saat": calculated_hours
                    })
            
            st.markdown("---")
            st.markdown(f"🏷️ **{day} - Fatura / Gider Ekleme**")
            num_exp = st.number_input(f"{day} gider/fiş sayısı", min_value=0, max_value=5, value=0, key=f"num_exp_{day}_{week_no}")
            
            for j in range(int(num_exp)):
                e_cols = st.columns([2, 1.5, 2.5])
                with e_cols[0]:
                    exp_desc = st.selectbox("Gider Açıklaması", st.session_state.expense_categories, key=f"exp_desc_{day}_{j}_{week_no}")
                with e_cols[1]:
                    exp_amount = st.number_input("Tutar (€)", min_value=0.0, value=10.0, step=1.0, key=f"exp_amt_{day}_{j}_{week_no}")
                with e_cols[2]:
                    exp_file = st.file_uploader(f"Fiş/Ekran Görseli", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{j}_{week_no}")
                
                if exp_amount > 0:
                    doc_code = f"Document {exp_counter}"
                    exp_counter += 1
                    all_expenses.append({
                        "Gün": day,
                        "Proje": proj if 'proj' in locals() else project_options[0],
                        "Kod": doc_code,
                        "Açıklama": exp_desc,
                        "Tutar": exp_amount,
                        "Görsel": exp_file
                    })

    st.session_state.weekly_data[current_week_key] = {
        "entries": all_entries,
        "expenses": all_expenses
    }

with tab_preview:
    st.header(f"👀 Önizleme ve Kontrol (Week {week_no} - {sel_year})")
    
    if all_entries:
        total_weekly_worker_hours = {}
        for item in all_entries:
            w_name = item["Çalışan"]
            total_weekly_worker_hours[w_name] = total_weekly_worker_hours.get(w_name, 0.0) + item["Saat"]
        
        global_summary_str = " | ".join([f"**{w}:** {hrs} saat" for w, hrs in total_weekly_worker_hours.items()])
        st.success(f"📊 **Haftalık Toplam Çalışan Saatleri:** {global_summary_str}")
        st.markdown("---")
        
        df_entries = pd.DataFrame(all_entries)
        unique_projects = df_entries["Proje"].unique()
        
        for proj in unique_projects:
            st.subheader(f"📁 Proje: {proj}")
            proj_e = [e for e in all_entries if e["Proje"] == proj]
            proj_ex = [ex for ex in all_expenses if ex["Proje"] == proj]
            
            total_h = sum(item["Saat"] for item in proj_e)
            total_c = sum(item["Tutar"] for item in proj_ex)
            
            worker_hours = {}
            for item in proj_e:
                w_name = item["Çalışan"]
                worker_hours[w_name] = worker_hours.get(w_name, 0.0) + item["Saat"]
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Proje Toplam Saati", f"{total_h} saat")
            col_m2.metric("Proje Toplam Gider", f"€{total_c:.2f}")
            
            w_str_summary = " | ".join([f"**{w}:** {hrs} saat" for w, hrs in worker_hours.items()])
            st.info(f"👥 **Bu Projedeki Dağılım:** {w_str_summary}")
            
            st.write("**Çalışma Detayları:**")
            st.dataframe(pd.DataFrame(proj_e)[["Gün", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]])
            
            if proj_ex:
                st.write("**Gider Detayları:**")
                st.dataframe(pd.DataFrame(proj_ex)[["Gün", "Kod", "Açıklama", "Tutar"]])
            st.markdown("---")
    else:
        st.info("Bu hafta için henüz çalışma kaydı girilmedi.")

def create_pdf(project_name, entries, expenses, week, year):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555555'))
    
    header_left_elements = []
    if st.session_state.comp_logo is not None:
        try:
            st.session_state.comp_logo.seek(0)
            pil_logo = PILImage.open(st.session_state.comp_logo)
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
        table_content.append([
            Paragraph(d_nl, sub_style),
            Paragraph(e["Çalışan"], sub_style),
            Paragraph(e["Başlangıç"], sub_style),
            Paragraph(e["Mola"], sub_style),
            Paragraph(e["Bitiş"], sub_style),
            Paragraph(str(e["Saat"]), sub_style),
        ])
        total_hours += e["Saat"]
        
    t_main = Table(table_content, colWidths=[90, 95, 70, 70, 70, 140])
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
            exp_table_content.append([
                Paragraph(f"<b>{ex['Kod']}</b>", sub_style),
                Paragraph(d_nl, sub_style),
                Paragraph(ex["Açıklama"], sub_style),
                Paragraph(f"€{ex['Tutar']:.2f}", sub_style)
            ])
            total_cost += ex["Tutar"]
        t_exp = Table(exp_table_content, colWidths=[80, 80, 275, 70])
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
    
    receipts_with_images = [ex for ex in proj_expenses if ex["Görsel"] is not None]
    if receipts_with_images:
        story.append(PageBreak())
        story.append(Paragraph("<b>Bonnetjes en Facturen (Documenten)</b>", ParagraphStyle('ReceiptTitle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#1F4E78'))))
        story.append(Spacer(1, 8))
        
        img_table_data = []
        row_cells = []
        
        for idx, ex in enumerate(receipts_with_images):
            try:
                ex["Görsel"].seek(0)
                pil_rec = PILImage.open(ex["Görsel"]).convert("RGB")
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
                
                rec_io = io.BytesIO()
                pil_rec.save(rec_io, format='JPEG')
                rec_io.seek(0)
                
                aspect = h_img / w_img
                img_w = 220
                img_h = img_w * aspect
                if img_h > 210:
                    img_h = 210
                    img_w = img_h / aspect
                    
                rl_rec_img = RLImage(rec_io, width=img_w, height=img_h)
                
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

st.markdown("---")
st.subheader("📥 Raporu PDF Olarak İndir (Nederlands)")

if all_entries:
    df = pd.DataFrame(all_entries)
    unique_projects = df["Proje"].unique()
    
    for proj in unique_projects:
        proj_entries = [e for e in all_entries if e["Proje"] == proj]
        
        pdf_file = create_pdf(proj, proj_entries, all_expenses, week_no, sel_year)
        
        col_dl1, col_dl2 = st.columns([3, 1])
        with col_dl1:
            btn_clicked = st.download_button(
                label=f"📥 {proj} - Werkbon PDF İndir (Week {week_no})",
                data=pdf_file,
                file_name=f"Werkbon_Week{week_no}_{sel_year}_{proj.replace(' ', '_').replace('(', '').replace(')', '')}.pdf",
                mime="application/pdf",
                key=f"btn_{proj}_{week_no}"
            )
        with col_dl2:
            if st.button(f"✅ Tamamlandı İşaretle", key=f"mark_{proj}_{week_no}"):
                st.session_state.completed_weeks.add(current_week_key)
                st.success("Hafta tamamlandı işaretlendi!")
                st.rerun()
else:
    st.info("Bu hafta için henüz kayıt bulunmuyor.")
