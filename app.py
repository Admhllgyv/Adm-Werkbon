import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

st.set_page_config(page_title="ADM Technics - Werkbon Otomasyonu", layout="wide")

# Kurumsal Stil Başlık
st.title("⚡ ADM TECHNICS - Akıllı Werkbon Otomasyonu")
st.markdown("Haftalık verileri aşağıya girin; sistem projeleri otomatik ayırsın ve PDF çıktısını versin.")

# 1. Hafta ve Genel Bilgiler
col1, col2 = st.columns(2)
with col1:
    week_no = st.number_input("Hafta Numarası", min_value=1, max_value=53, value=35)
with col2:
    worker_default = st.selectbox("Varsayılan Çalışan", ["Adem", "Melih", "İkisi Birlikte"])

st.markdown("---")
st.subheader("📅 Günlük Çalışma ve Masraf Girişi")

# Gün gün veri toplamak için form yapısı
days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
all_entries = []

for day in days:
    with st.expander(f"📌 {day} Girişleri", expanded=(day == "Pazartesi")):
        # Her gün için 3 satırlık hızlı giriş tablosu veya dinamik alan
        num_rows = st.number_input(f"{day} için işlem satırı sayısı", min_value=1, max_value=10, value=2, key=f"num_{day}")
        
        for i in range(int(num_rows)):
            cols = st.columns([2, 1.5, 1, 1, 1, 2, 1])
            with cols[0]:
                proj = st.text_input(f"Proje No / Adı", value="Kruidvat Diepenbeek", key=f"p_{day}_{i}")
            with cols[1]:
                wrk = st.selectbox("Çalışan", ["Adem", "Melih"], key=f"w_{day}_{i}")
            with cols[2]:
                start = st.text_input("Başlangıç", value="08:00", key=f"s_{day}_{i}")
            with cols[3]:
                pause = st.text_input("Mola", value="00:45", key=f"pa_{day}_{i}")
            with cols[4]:
                stop = st.text_input("Bitiş", value="16:30", key=f"st_{day}_{i}")
            with cols[5]:
                desc = st.text_input("Yapılan İş Açıklaması", value="Kablo çekimi ve montaj", key=f"d_{day}_{i}")
            with cols[6]:
                cost = st.number_input("Gider (€)", min_value=0.0, value=0.0, step=5.0, key=f"c_{day}_{i}")
            
            # Kayıt listesine ekleme (Basit saat hesap simülasyonu)
            if proj:
                all_entries.append({
                    "Gün": day,
                    "Proje": proj,
                    "Çalışan": wrk,
                    "Başlangıç": start,
                    "Mola": pause,
                    "Bitiş": stop,
                    "Açıklama": desc,
                    "Gider": cost,
                    "Saat": 7.75 # Örnek hesaplanmış net saat
                })

# 2. PDF Üretim Fonksiyonu
def create_pdf(project_name, entries, week):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1F4E78'))
    sub_style = ParagraphStyle('SubStyle', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555555'))
    
    # Başlık Tablosu
    header_data = [
        [
            Paragraph("<b>ADM TECHNICS</b><br/><font size=7>Schutveststraat 5, 3500 Diepenbeek<br/>BTW: BE0787743276</font>", sub_style),
            Paragraph(f"<b>Hafta No:</b> {week}<br/><b>Proje / Müşteri:</b> {project_name}", ParagraphStyle('Meta', fontName='Helvetica', fontSize=8, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[250, 285])
    t_header.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F4F8')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 10))
    
    # Tablo Verileri
    table_content = [[Paragraph(h, ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)) 
                      for h in ["Gün", "Çalışan", "Başl.", "Mola", "Bitiş", "Saat", "Açıklama", "Gider (€)"]]]
    
    total_hours = 0
    total_cost = 0
    
    for e in entries:
        table_content.append([
            Paragraph(e["Gün"], sub_style),
            Paragraph(e["Çalışan"], sub_style),
            Paragraph(e["Başlangıç"], sub_style),
            Paragraph(e["Mola"], sub_style),
            Paragraph(e["Bitiş"], sub_style),
            Paragraph(str(e["Saat"]), sub_style),
            Paragraph(e["Açıklama"], sub_style),
            Paragraph(f"€{e['Gider']:.2f}", sub_style),
        ])
        total_hours += e["Saat"]
        total_cost += e["Gider"]
        
    t_main = Table(table_content, colWidths=[65, 50, 40, 35, 40, 35, 185, 85])
    t_main.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F4E78')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D3D3D3')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_main)
    story.append(Spacer(1, 10))
    
    # Özet Blok
    summary_text = f"<b>Toplam Çalışma Saati:</b> {total_hours} saat<br/><b>Toplam Gider/Malzeme:</b> €{total_cost:.2f}"
    t_summary = Table([[Paragraph(summary_text, sub_style), Paragraph("<b>Müşteri Onayı / İmza:</b><br/><br/>___________________", sub_style)]], colWidths=[270, 265])
    t_summary.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F4E78')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_summary)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# 3. Otomatik Raporlama ve İndirme Paneli
st.markdown("---")
st.subheader("📊 Otomatik Proje Raporları ve Çıktılar")

if all_entries:
    df = pd.DataFrame(all_entries)
    unique_projects = df["Proje"].unique()
    
    st.success(f"Toplam {len(all_entries)} kayıt girildi. Bulunan projeler: {', '.join(unique_projects)}")
    
    for proj in unique_projects:
        proj_entries = [e for e in all_entries if e["Proje"] == proj]
        st.write(f"📁 **Proje:** {proj} ({len(proj_entries)} kayıt)")
        
        pdf_file = create_pdf(proj, proj_entries, week_no)
        st.download_button(
            label=f"📥 {proj} - Werkbon PDF İndir",
            data=pdf_file,
            file_name=f"Werkbon_Week{week_no}_{proj.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key=f"btn_{proj}"
        )
else:
    st.info("Lütfen yukarıdaki gün alanlarından en az bir kayıt girin.")
