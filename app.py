import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage

st.set_page_config(page_title="ADM Technics - Werkbon & Ayarlar", layout="wide")

# Session State Initialization for Settings
if 'comp_name' not in st.session_state:
    st.session_state.comp_name = "ADM TECHNICS"
if 'comp_address' not in st.session_state:
    st.session_state.comp_address = "Schutveststraat 5, 3500 Diepenbeek"
if 'comp_btw' not in st.session_state:
    st.session_state.comp_btw = "BE0787743276"
if 'comp_logo' not in st.session_state:
    st.session_state.comp_logo = None

# Tabs for Navigation
tab_main, tab_settings = st.tabs(["📝 Werkbon & Gider Girişi", "⚙️ Firma Ayarları"])

with tab_settings:
    st.header("⚙️ Firma Bilgileri ve Logo Ayarları")
    st.markdown("Bilgilerinizi ve logonuzu buradan güncelleyebilirsiniz. Değişiklikler anında PDF çıktısına yansır.")
    
    st.session_state.comp_name = st.text_input("Firma Adı", value=st.session_state.comp_name)
    st.session_state.comp_address = st.text_input("Firma Adresi", value=st.session_state.comp_address)
    st.session_state.comp_btw = st.text_input("BTW Numarası", value=st.session_state.comp_btw)
    
    uploaded_logo = st.file_uploader("Firma Logosu Yükle (JPG / PNG)", type=["jpg", "jpeg", "png"])
    if uploaded_logo is not None:
        st.session_state.comp_logo = uploaded_logo
        st.success("Logo başarıyla yüklendi!")
    
    if st.session_state.comp_logo is not None:
        st.image(st.session_state.comp_logo, width=150, caption="Mevcut Logo")

with tab_main:
    st.title(f"⚡ {st.session_state.comp_name} - Akıllı Werkbon Otomasyonu")
    
    col1, col2 = st.columns(2)
    with col1:
        week_no = st.number_input("Hafta Numarası", min_value=1, max_value=53, value=35)
    with col2:
        default_worker = st.selectbox("Varsayılan Çalışan", ["Adem", "Melih", "İkisi Birlikte"])

    st.markdown("---")
    st.subheader("📅 Günlük Çalışma ve Fiş/Gider Girişi")

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
    all_entries = []
    all_expenses = []

    for day in days:
        with st.expander(f"📌 {day}", expanded=(day == "Pazartesi")):
            # Work items
            num_rows = st.number_input(f"{day} için çalışma satırı sayısı", min_value=1, max_value=10, value=1, key=f"num_{day}")
            for i in range(int(num_rows)):
                cols = st.columns([2, 1.5, 1, 1, 1, 2])
                with cols[0]:
                    proj = st.text_input("Proje / Müşteri", value="Kruidvat Diepenbeek", key=f"p_{day}_{i}")
                with cols[1]:
                    wrk = st.selectbox("Çalışan", ["Adem", "Melih"], key=f"w_{day}_{i}")
                with cols[2]:
                    start = st.text_input("Başl.", value="08:00", key=f"s_{day}_{i}")
                with cols[3]:
                    pause = st.text_input("Mola", value="00:45", key=f"pa_{day}_{i}")
                with cols[4]:
                    stop = st.text_input("Bitiş", value="16:30", key=f"st_{day}_{i}")
                with cols[5]:
                    desc = st.text_input("Yapılan İş Açıklaması", value="Kablo çekimi", key=f"d_{day}_{i}")
                
                if proj:
                    all_entries.append({
                        "Gün": day,
                        "Proje": proj,
                        "Çalışan": wrk,
                        "Başlangıç": start,
                        "Mola": pause,
                        "Bitiş": stop,
                        "Açıklama": desc,
                        "Saat": 7.75
                    })
            
            st.markdown("---")
            # Expenses for this day
            st.markdown(f"🏷️ **{day} - Gider / Fiş Ekleme**")
            num_exp = st.number_input(f"{day} için gider/fiş sayısı", min_value=0, max_value=5, value=0, key=f"num_exp_{day}")
            
            for j in range(int(num_exp)):
                e_cols = st.columns([2, 1.5, 2.5])
                with e_cols[0]:
                    exp_desc = st.text_input("Gider Açıklaması", value="Malzeme / Park", key=f"exp_desc_{day}_{j}")
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

    # PDF Generation Function
    def create_pdf(project_name, entries, expenses, week):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()
        
        sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555555'))
        
        # Header Table with Logo and Dynamic Company Details
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
                Paragraph(f"<b>Hafta No:</b> {week}<br/><b>Proje / Müşteri:</b> {project_name}", ParagraphStyle('Meta', fontName='Helvetica', fontSize=8, alignment=2))
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
        
        # Work Table
        table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                          for h in ["Gün", "Çalışan", "Başl.", "Mola", "Bitiş", "Saat", "Açıklama"]]]
        
        total_hours = 0
        for e in entries:
            table_content.append([
                Paragraph(e["Gün"], sub_style),
                Paragraph(e["Çalışan"], sub_style),
                Paragraph(e["Başlangıç"], sub_style),
                Paragraph(e["Mola"], sub_style),
                Paragraph(e["Bitiş"], sub_style),
                Paragraph(str(e["Saat"]), sub_style),
                Paragraph(e["Açıklama"], sub_style),
            ])
            total_hours += e["Saat"]
            
        t_main = Table(table_content, colWidths=[65, 50, 40, 35, 40, 35, 240])
        t_main.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E78')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_main)
        story.append(Spacer(1, 10))
        
        # Expenses Table if any
        proj_expenses = [ex for ex in expenses if ex["Proje"] == project_name]
        total_cost = 0
        if proj_expenses:
            story.append(Paragraph("<b>Malzeme ve Giderler:</b>", ParagraphStyle('ExpTitle', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1F4E78'))))
            story.append(Spacer(1, 4))
            exp_table_content = [[Paragraph("<b>Gün</b>", sub_style), Paragraph("<b>Açıklama</b>", sub_style), Paragraph("<b>Tutar (€)</b>", sub_style)]]
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

        # Summary Block
        summary_text = f"<b>Toplam Çalışma Saati:</b> {total_hours} saat<br/><b>Toplam Gider:</b> €{total_cost:.2f}"
        t_summary = Table([[Paragraph(summary_text, sub_style), Paragraph("<b>Müşteri Onayı / İmza:</b><br/><br/>___________________", sub_style)]], colWidths=[270, 265])
        t_summary.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_summary)
        
        # Receipt Images Appendix Pages
        receipts_with_images = [ex for ex in proj_expenses if ex["Görsel"] is not None]
        if receipts_with_images:
            story.append(PageBreak())
            story.append(Paragraph("<b>Fiş ve Fatura Görselleri</b>", ParagraphStyle('ReceiptTitle', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1F4E78'))))
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
                    story.append(Paragraph("[Görsel yüklenirken hata oluştu]", sub_style))
                    story.append(Spacer(1, 10))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    st.markdown("---")
    st.subheader("📊 Otomatik Proje Raporları ve Çıktılar")

    if all_entries:
        df = pd.DataFrame(all_entries)
        unique_projects = df["Proje"].unique()
        
        st.success(f"Toplam {len(all_entries)} çalışma kaydı ve {len(all_expenses)} gider kaydı bulundu.")
        
        for proj in unique_projects:
            proj_entries = [e for e in all_entries if e["Proje"] == proj]
            st.write(f"📁 **Proje:** {proj} ({len(proj_entries)} çalışma kaydı)")
            
            pdf_file = create_pdf(proj, proj_entries, all_expenses, week_no)
            st.download_button(
                label=f"📥 {proj} - Werkbon PDF İndir",
                data=pdf_file,
                file_name=f"Werkbon_Week{week_no}_{proj.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"btn_{proj}"
            )
    else:
        st.info("Lütfen yukarıdaki gün alanlarından en az bir çalışma kaydı girin.")
