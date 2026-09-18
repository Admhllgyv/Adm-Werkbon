import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage
from datetime import datetime, timedelta

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

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

# Time slot generators for 15-minute intervals
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

# Helper to calculate net hours
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

# Tabs for Navigation
tab_entry, tab_preview, tab_settings = st.tabs(["📝 Werkbon Girişi", "👀 Önizleme ve Kontrol", "⚙️ Firma & İşçi Ayarları"])

with tab_settings:
    st.header("⚙️ Firma e Çalışan Ayarları")
    
    st.subheader("Firma Bilgileri ve Logo")
    st.session_state.comp_name = st.text_input("Firma Adı", value=st.session_state.comp_name)
    st.session_state.comp_address = st.text_input("Firma Adresi", value=st.session_state.comp_address)
    st.session_state.comp_btw = st.text_input("BTW Numarası", value=st.session_state.comp_btw)
    
    uploaded_logo = st.file_uploader("Firma Logosu Yükle (JPG / PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        st.session_state.comp_logo = uploaded_logo
        st.success("Logo başarıyla güncellendi!")
    
    if st.session_state.comp_logo is not None:
        st.image(st.session_state.comp_logo, width=150, caption="Mevcut Logo")
        
    st.markdown("---")
    st.subheader("Çalışan Listesi Yönetimi")
    col_w1, col_w2 = st.columns([2, 1])
    with col_w1:
        new_worker_name = st.text_input("Yeni Çalışan Adı")
    with col_w2:
        st.write("")
        st.write("")
        if st.button("Çalışan Ekle"):
            if new_worker_name and new_worker_name not in st.session_state.workers:
                st.session_state.workers.append(new_worker_name)
                st.rerun()
                
    st.write("Mevcut Çalışanlar:")
    for w in st.session_state.workers:
        cols_w = st.columns([3, 1])
        with cols_w[0]:
            st.write(f"- {w}")
        with cols_w[1]:
            if len(st.session_state.workers) > 1:
                if st.button("Sil", key=f"del_w_{w}"):
                    st.session_state.workers.remove(w)
                    st.rerun()

with tab_entry:
    st.title(f"⚡ {st.session_state.comp_name} - Akıllı Werkbon Otomasyonu")
    
    col1, _ = st.columns(2)
    with col1:
        week_no = st.number_input("Hafta Numarası (Weeknummer)", min_value=1, max_value=53, value=35)

    st.markdown("---")
    st.subheader("📅 Günlük Çalışma ve Fiş/Gider Girişi")

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []

    for day in days:
        with st.expander(f"📌 {day}", expanded=(day == "Pazartesi")):
            num_rows = st.number_input(f"{day} çalışma satırı sayısı", min_value=1, max_value=10, value=1, key=f"num_{day}")
            for i in range(int(num_rows)):
                cols = st.columns([2, 1.5, 1.2, 1.2, 1.2])
                with cols[0]:
                    proj = st.text_input("Proje / Müşteri Adı", value="Kruidvat Diepenbeek", key=f"p_{day}_{i}")
                with cols[1]:
                    wrk = st.selectbox("Çalışan", st.session_state.workers, key=f"w_{day}_{i}")
                
                # Start Time Selection (Default 07:00 -> index 13)
                with cols[2]:
                    s_choice = st.selectbox("Başlangıç", start_slots, index=13, key=f"s_choice_{day}_{i}") 
                    if s_choice == "Manuel Giriş":
                        start = st.text_input("Örn: 07:00", value="07:00", key=f"s_man_{day}_{i}")
                    else:
                        start = s_choice

                # Pause Selection (Default 00:45 -> index 2)
                with cols[3]:
                    p_choice = st.selectbox("Mola", pause_slots, index=2, key=f"p_choice_{day}_{i}")
                    if p_choice == "Manuel Giriş":
                        pause = st.text_input("Örn: 00:45", value="00:45", key=f"p_man_{day}_{i}")
                    else:
                        pause = p_choice

                # End Time Selection (Default 15:45 -> index 15)
                with cols[4]:
                    e_choice = st.selectbox("Bitiş", end_slots, index=15, key=f"e_choice_{day}_{i}")
                    if e_choice == "Manuel Giriş":
                        stop = st.text_input("Örn: 15:45", value="15:45", key=f"e_man_{day}_{i}")
                    else:
                        stop = e_choice
                
                calculated_hours = calculate_net_hours(start, pause, stop)
                st.caption(f"⏱️ Hesaplanan Net Çalışma Saati: **{calculated_hours} saat** ({start} - {stop}, Mola: {pause})")

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
            num_exp = st.number_input(f"{day} gider/fiş sayısı", min_value=0, max_value=5, value=0, key=f"num_exp_{day}")
            
            for j in range(int(num_exp)):
                e_cols = st.columns([2, 1.5, 2.5])
                with e_cols[0]:
                    exp_desc = st.text_input("Gider Açıklaması", value="Malzeme", key=f"exp_desc_{day}_{j}")
                with e_cols[1]:
                    exp_amount = st.number_input("Tutar (€)", min_value=0.0, value=10.0, step=1.0, key=f"exp_amt_{day}_{j}")
                with e_cols[2]:
                    exp_file = st.file_uploader(f"Fiş Görseli (JPG/PNG)", type=["jpg", "jpeg", "png"], key=f"exp_file_{day}_{j}")
                
                if exp_amount > 0:
                    all_expenses.append({
                        "Gün": day,
                        "Proje": proj if 'proj' in locals() else "Genel Proje",
                        "Açıklama": exp_desc,
                        "Tutar": exp_amount,
                        "Görsel": exp_file
                    })

with tab_preview:
    st.header("👀 Önizleme ve Kontrol Paneli")
    st.markdown("PDF indirmeden önce girilen saatleri ve masrafları buradan kontrol edebilirsiniz.")
    
    if all_entries:
        df_entries = pd.DataFrame(all_entries)
        unique_projects = df_entries["Proje"].unique()
        
        for proj in unique_projects:
            st.subheader(f"📁 Proje: {proj}")
            proj_e = [e for e in all_entries if e["Proje"] == proj]
            proj_ex = [ex for ex in all_expenses if ex["Proje"] == proj]
            
            total_h = sum(item["Saat"] for item in proj_e)
            total_c = sum(item["Tutar"] for item in proj_ex)
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Toplam Çalışma Saati", f"{total_h} saat")
            col_m2.metric("Toplam Gider / Malzeme", f"€{total_c:.2f}")
            
            st.write("**Çalışma Detayları:**")
            st.dataframe(pd.DataFrame(proj_e)[["Gün", "Çalışan", "Başlangıç", "Mola", "Bitiş", "Saat"]])
            
            if proj_ex:
                st.write("**Gider Detayları:**")
                st.dataframe(pd.DataFrame(proj_ex)[["Gün", "Açıklama", "Tutar"]])
            st.markdown("---")
    else:
        st.info("Henüz çalışma kaydı girilmedi.")

# PDF Generation Function (Flamanca / Dutch)
def create_pdf(project_name, entries, expenses, week):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555555'))
    
    header_left_elements = []
    if st.session_state.comp_logo is not None:
        try:
            st.session_state.comp_logo.seek(0)
            pil_logo = PILImage.open(st.session_state.comp_logo)
            img_io = io.BytesIO()
            pil_logo.save(img_io, format='JPEG')
            img_io.seek(0)
            rl_img = RLImage(img_io, width=45, height=45)
            header_left_elements.append(rl_img)
        except Exception:
            pass
    
    header_text = f"<b>{st.session_state.comp_name}</b><br/><font size=7>{st.session_state.comp_address}<br/>BTW: {st.session_state.comp_btw}</font>"
    header_left_elements.append(Paragraph(header_text, sub_style))
    
    header_data = [
        [
            header_left_elements,
            Paragraph(f"<b>Weeknummer:</b> {week}<br/><b>Project / Klant:</b> {project_name}", ParagraphStyle('Meta', fontName='Helvetica', fontSize=8, alignment=2))
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
    
    # Dutch Table Headers
    table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                      for h in ["Dag", "Medewerker", "Start", "Pauze", "Einde", "Uren"]]]
    
    total_hours = 0
    for e in entries:
        table_content.append([
            Paragraph(e["Gün"], sub_style),
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
    
    # Expenses Table in Dutch
    proj_expenses = [ex for ex in expenses if ex["Proje"] == project_name]
    total_cost = 0
    if proj_expenses:
        story.append(Paragraph("<b>Materialen en Kosten:</b>", ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1F4E78'))))
        story.append(Spacer(1, 4))
        exp_table_content = [[Paragraph("<b>Dag</b>", sub_style), Paragraph("<b>Omschrijving</b>", sub_style), Paragraph("<b>Bedrag (€)</b>", sub_style)]]
        for ex in proj_expenses:
            exp_table_content.append([
                Paragraph(ex["Gün"], sub_style),
                Paragraph(ex["Açıklama"], sub_style),
                Paragraph(f"€{ex['Tutar']:.2f}", sub_style)
            ])
            total_cost += ex["Tutar"]
        t_exp = Table(exp_table_content, colWidths=[100, 335, 70])
        t_exp.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E9ECEF')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_exp)
        story.append(Spacer(1, 10))

    # Summary Block in Dutch
    summary_text = f"<b>Totale uren:</b> {total_hours} uur<br/><b>Totale kosten:</b> €{total_cost:.2f}"
    t_summary = Table([[Paragraph(summary_text, sub_style), Paragraph("<b>Klantakkoord / Handtekening:</b><br/><br/>___________________", sub_style)]], colWidths=[270, 265])
    t_summary.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_summary)
    
    # Receipt Images Appendix
    receipts_with_images = [ex for ex in proj_expenses if ex["Görsel"] is not None]
    if receipts_with_images:
        story.append(PageBreak())
        story.append(Paragraph("<b>Bonnetjes en Facturen</b>", ParagraphStyle('ReceiptTitle', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1F4E78'))))
        story.append(Spacer(1, 10))
        for ex in receipts_with_images:
            story.append(Paragraph(f"<b>{ex['Gün']} - {ex['Açıklama']} (€{ex['Tutar']:.2f}):</b>", sub_style))
            story.append(Spacer(1, 4))
            try:
                ex["Görsel"].seek(0)
                pil_rec = PILImage.open(ex["Görsel"])
                rec_io = io.BytesIO()
                pil_rec.save(rec_io, format='JPEG')
                rec_io.seek(0)
                w, h = pil_rec.size
                aspect = h / w
                img_w = 350
                img_h = img_w * aspect
                if img_h > 380:
                    img_h = 380
                    img_w = img_h / aspect
                rl_rec_img = RLImage(rec_io, width=img_w, height=img_h)
                story.append(rl_rec_img)
                story.append(Spacer(1, 15))
            except Exception:
                story.append(Paragraph("[Fout bij laden afbeelding]", sub_style))
                story.append(Spacer(1, 10))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Download Section
st.markdown("---")
st.subheader("📥 Proje Raporları ve PDF İndir (Flamanca)")

if all_entries:
    df = pd.DataFrame(all_entries)
    unique_projects = df["Proje"].unique()
    
    for proj in unique_projects:
        proj_entries = [e for e in all_entries if e["Proje"] == proj]
        
        pdf_file = create_pdf(proj, proj_entries, all_expenses, week_no)
        st.download_button(
            label=f"📥 {proj} - Werkbon PDF İndir",
            data=pdf_file,
            file_name=f"Werkbon_Week{week_no}_{proj.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key=f"btn_{proj}"
        )
