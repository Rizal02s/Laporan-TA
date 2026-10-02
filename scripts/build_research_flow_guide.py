from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "docs" / "Panduan_Alur_Penelitian_VAEP_Track.docx"
ASSET_DIR = (
    Path.home()
    / "AppData"
    / "Local"
    / "Temp"
    / "vaep_track_research_flow_assets"
)

INK = "1F2933"
TEAL = "176B6B"
TEAL_DARK = "0F4F4F"
TEAL_LIGHT = "E5F2F1"
CORAL = "C95B4A"
CORAL_LIGHT = "F8E9E6"
GOLD = "B78324"
GOLD_LIGHT = "F7F0DF"
GRAY = "5E6A71"
LIGHT_GRAY = "F3F5F6"
BORDER = "D9DEE2"
WHITE = "FFFFFF"


def pil_font(size: int, bold: bool = False):
    filename = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size=size)


def draw_centered_multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font,
    fill: str,
    spacing: int = 8,
) -> None:
    draw.multiline_text(
        xy,
        text,
        font=font,
        fill=fill,
        anchor="mm",
        align="center",
        spacing=spacing,
    )


def set_font(run, name: str = "Aptos", size: float | None = None) -> None:
    run.font.name = name
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), name)
    r_fonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_borders(cell, color: str = BORDER, size: str = "5") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=105, start=120, bottom=105, end=120) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (
        ("top", top),
        ("start", start),
        ("bottom", bottom),
        ("end", end),
    ):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_row_cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def set_cell_width(cell, width_cm: float) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def style_table(table, widths_cm: list[float] | None = None) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_repeat_table_header(table.rows[0])
    for row_index, row in enumerate(table.rows):
        set_row_cant_split(row)
        for column_index, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if widths_cm:
                set_cell_width(cell, widths_cm[column_index])
            set_cell_borders(cell)
            set_cell_margins(cell)
            if row_index == 0:
                set_cell_shading(cell, TEAL_DARK)
            elif row_index % 2 == 0:
                set_cell_shading(cell, "F4F8F8")
            else:
                set_cell_shading(cell, WHITE)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.08
                for run in paragraph.runs:
                    set_font(run, size=8.8)
                    if row_index == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor.from_string(WHITE)


def add_table(
    doc: Document,
    headers: list[str],
    rows: list[list[object]],
    widths_cm: list[float] | None = None,
):
    table = doc.add_table(rows=1, cols=len(headers))
    for index, value in enumerate(headers):
        table.rows[0].cells[index].text = str(value)
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = str(value)
    style_table(table, widths_cm)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(1)
    return table


def add_bullet(doc: Document, text: str, level: int = 0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    paragraph = doc.add_paragraph(style=style)
    paragraph.add_run(text)


def add_number(doc: Document, number: int, text: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.75)
    paragraph.paragraph_format.first_line_indent = Cm(-0.75)
    paragraph.paragraph_format.space_after = Pt(3)
    number_run = paragraph.add_run(f"{number}.  ")
    number_run.bold = True
    paragraph.add_run(text)


def add_lead_paragraph(doc: Document, lead: str, text: str) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(lead)
    run.bold = True
    run.font.color.rgb = RGBColor.from_string(TEAL_DARK)
    paragraph.add_run(text)


def add_caption(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph(text)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(8)
    for run in paragraph.runs:
        set_font(run, size=8.5)
        run.font.italic = True
        run.font.color.rgb = RGBColor.from_string(GRAY)


def add_picture(
    doc: Document,
    path: Path,
    width_inches: float,
    caption: str,
    alt_text: str,
) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    picture = paragraph.add_run().add_picture(str(path), width=Inches(width_inches))
    picture._inline.docPr.set("descr", alt_text)
    picture._inline.docPr.set("title", caption)
    add_caption(doc, caption)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Halaman ")
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def create_pipeline_figure(path: Path) -> None:
    image = Image.new("RGB", (1800, 2200), "white")
    draw = ImageDraw.Draw(image)
    draw_centered_multiline(
        draw,
        (900, 80),
        "Alur penelitian VAEP-Track dari data hingga kesimpulan",
        pil_font(46, bold=True),
        "#1F2933",
    )

    boxes = [
        (900, 245, 1180, "1  Data IDSSE", "event dan tracking tujuh pertandingan", "#E5F2F1"),
        (900, 475, 1180, "2  Deteksi turnover", "perubahan penguasaan saat bola hidup", "#E5F2F1"),
        (900, 705, 1180, "3  Episode terstandar", "window -2 s sampai +2 s dan audit validitas", "#E5F2F1"),
        (900, 935, 1180, "4  Anotasi perilaku", "gegenpressing 1, bukan 0, ragu -1", "#F7F0DF"),
        (900, 1165, 1180, "5  Split per pertandingan", "train, validation, dan test bebas leakage", "#F7F0DF"),
        (480, 1435, 720, "6A  Baseline", "12 fitur tekanan, logistic regression, XGBoost", "#F8E9E6"),
        (1320, 1435, 720, "6B  Temporal GNN", "GCN per frame, pooling, lalu GRU", "#F8E9E6"),
        (900, 1710, 1180, "7  Evaluasi", "threshold validation dan metrik match-level", "#E5F2F1"),
        (900, 1940, 1180, "8  Efektivitas", "quick regain dan keputusan VAEP final", "#E5F2F1"),
    ]

    def box(cx, cy, width, title, subtitle, fill):
        height = 150
        bounds = (cx - width // 2, cy - height // 2, cx + width // 2, cy + height // 2)
        draw.rounded_rectangle(bounds, radius=22, fill=fill, outline="#176B6B", width=4)
        draw.text((cx, cy - 25), title, font=pil_font(34, bold=True), fill="#1F2933", anchor="mm")
        draw.text((cx, cy + 27), subtitle, font=pil_font(25), fill="#4B5563", anchor="mm")

    for values in boxes:
        box(*values)

    def arrow(start, end):
        draw.line([start, end], fill="#5E6A71", width=5)
        x2, y2 = end
        angle = np.arctan2(y2 - start[1], x2 - start[0])
        length = 20
        for offset in (-0.55, 0.55):
            point = (
                x2 - length * np.cos(angle + offset),
                y2 - length * np.sin(angle + offset),
            )
            draw.line([point, end], fill="#5E6A71", width=5)

    for start, end in [
        ((900, 320), (900, 400)),
        ((900, 550), (900, 630)),
        ((900, 780), (900, 860)),
        ((900, 1010), (900, 1090)),
        ((900, 1240), (480, 1360)),
        ((900, 1240), (1320, 1360)),
        ((480, 1510), (820, 1635)),
        ((1320, 1510), (980, 1635)),
        ((900, 1785), (900, 1865)),
    ]:
        arrow(start, end)

    draw_centered_multiline(
        draw,
        (900, 2130),
        "Prinsip utama: perilaku gegenpressing dan outcome quick regain tidak disamakan.",
        pil_font(27, bold=True),
        "#0F4F4F",
    )
    image.save(path, quality=95)


def create_label_matrix(path: Path) -> None:
    image = Image.new("RGB", (1800, 1250), "white")
    draw = ImageDraw.Draw(image)
    left, top, cell_w, cell_h = 270, 150, 720, 440
    cells = [
        (left, top, "#E5F2F1", "Bukan gegenpressing\nQuick regain berhasil", "Regain dapat terjadi karena error lawan,\nbola liar, atau duel, bukan tekanan kolektif."),
        (left + cell_w, top, "#CDE7E4", "Gegenpressing\nQuick regain berhasil", "Perilaku tekanan muncul dan hasilnya\npenguasaan kembali dalam lima detik."),
        (left, top + cell_h, "#F3F5F6", "Bukan gegenpressing\nQuick regain gagal", "Tim mundur atau reorganisasi dan tidak\nmerebut bola kembali dengan cepat."),
        (left + cell_w, top + cell_h, "#F8E9E6", "Gegenpressing\nQuick regain gagal", "Upaya tekanan terlihat, tetapi lawan\nberhasil keluar atau mempertahankan bola."),
    ]
    for x, y, fill, title, body in cells:
        draw.rectangle((x, y, x + cell_w, y + cell_h), fill=fill, outline="#B8C1C7", width=4)
        draw_centered_multiline(draw, (x + cell_w / 2, y + 150), title, pil_font(34, bold=True), "#1F2933", 7)
        draw_centered_multiline(draw, (x + cell_w / 2, y + 305), body, pil_font(25), "#4B5563", 9)
    draw.text((left + cell_w / 2, 100), "Bukan gegenpressing", font=pil_font(28, bold=True), fill="#1F2933", anchor="mm")
    draw.text((left + 1.5 * cell_w, 100), "Gegenpressing", font=pil_font(28, bold=True), fill="#1F2933", anchor="mm")
    draw.text((90, top + cell_h / 2), "Quick regain\nberhasil", font=pil_font(25, bold=True), fill="#1F2933", anchor="mm", align="center")
    draw.text((90, top + 1.5 * cell_h), "Quick regain\ngagal", font=pil_font(25, bold=True), fill="#1F2933", anchor="mm", align="center")
    draw.text((left + cell_w, 1110), "Label perilaku gegenpressing", font=pil_font(30, bold=True), fill="#0F4F4F", anchor="mm")
    image.save(path, quality=95)


def create_graph_figure(path: Path) -> None:
    rng = np.random.default_rng(7)
    image = Image.new("RGB", (2400, 980), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (1200, 65),
        "Satu episode adalah urutan 101 graph dengan node yang konsisten",
        font=pil_font(42, bold=True),
        fill="#1F2933",
        anchor="mm",
    )
    times = ["t = -2,00 s", "t = 0,00 s", "t = +2,00 s"]
    panel_w, panel_h = 700, 600
    for index, time_label in enumerate(times):
        x0 = 80 + index * 790
        y0 = 170
        draw.rectangle((x0, y0, x0 + panel_w, y0 + panel_h), outline="#AEB7BC", width=4)
        draw.line((x0 + panel_w / 2, y0, x0 + panel_w / 2, y0 + panel_h), fill="#D0D5D8", width=3)
        red = rng.uniform([0.12, 0.17], [0.88, 0.78], size=(11, 2))
        blue = rng.uniform([0.12, 0.17], [0.88, 0.78], size=(11, 2))
        ball = np.array([0.55 + 0.06 * index, 0.48 + 0.02 * index])
        points = np.vstack([red, blue, ball])
        for source in range(len(points)):
            distances = np.linalg.norm(points - points[source], axis=1)
            for target in np.argsort(distances)[1:5]:
                sx = x0 + points[source, 0] * panel_w
                sy = y0 + (1 - points[source, 1]) * panel_h
                tx = x0 + points[target, 0] * panel_w
                ty = y0 + (1 - points[target, 1]) * panel_h
                draw.line((sx, sy, tx, ty), fill="#D3D8DB", width=2)
        for x, y in red:
            px, py = x0 + x * panel_w, y0 + (1 - y) * panel_h
            draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill="#C95B4A", outline="white", width=2)
        for x, y in blue:
            px, py = x0 + x * panel_w, y0 + (1 - y) * panel_h
            draw.polygon([(px, py - 13), (px - 12, py + 11), (px + 12, py + 11)], fill="#2E7E9B", outline="white")
        px, py = x0 + ball[0] * panel_w, y0 + (1 - ball[1]) * panel_h
        draw.ellipse((px - 14, py - 14, px + 14, py + 14), fill="#1F2933", outline="white", width=3)
        draw.text((x0 + panel_w / 2, y0 + panel_h + 45), time_label, font=pil_font(29, bold=True), fill="#1F2933", anchor="mm")
    draw.text(
        (1200, 920),
        "Setiap node terhubung ke empat tetangga spasial terdekat pada setiap frame",
        font=pil_font(27),
        fill="#4B5563",
        anchor="mm",
    )
    image.save(path, quality=95)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.9)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(10.2)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.14

    style_specs = {
        "Title": (22, 0, 9),
        "Heading 1": (15, 14, 6),
        "Heading 2": (12, 10, 4),
        "Heading 3": (10.5, 8, 3),
    }
    for style_name, (size, before, after) in style_specs.items():
        style = styles[style_name]
        style.font.name = "Aptos Display" if style_name != "Heading 3" else "Aptos"
        style._element.rPr.rFonts.set(qn("w:ascii"), style.font.name)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), style.font.name)
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    title_p_pr = styles["Title"].element.get_or_add_pPr()
    title_border = title_p_pr.find(qn("w:pBdr"))
    if title_border is not None:
        title_p_pr.remove(title_border)

    for list_style in ("List Bullet", "List Bullet 2", "List Number"):
        style = styles[list_style]
        style.font.name = "Aptos"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
        style.font.size = Pt(10.2)
        style.paragraph_format.space_after = Pt(3)

    header = section.header.paragraphs[0]
    header.text = "VAEP-Track  |  Panduan Konseptual Penelitian"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        set_font(run, size=8)
        run.font.color.rgb = RGBColor.from_string(GRAY)

    footer = section.footer.paragraphs[0]
    add_page_number(footer)
    for run in footer.runs:
        set_font(run, size=8)
        run.font.color.rgb = RGBColor.from_string(GRAY)


def add_cover(doc: Document) -> None:
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(40)
    title.add_run("Panduan Alur Penelitian VAEP Track")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(16)
    run = subtitle.add_run(
        "Memahami deteksi dan valuasi efektivitas gegenpressing dari data IDSSE hingga temporal GNN"
    )
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor.from_string(TEAL_DARK)

    topic = doc.add_paragraph()
    topic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    topic.paragraph_format.left_indent = Cm(1.2)
    topic.paragraph_format.right_indent = Cm(1.2)
    topic.add_run(
        "Dokumen pendamping untuk penelitian berjudul VAEP-Track Deteksi dan Valuasi "
        "Efektivitas Gegenpressing pada Transisi Kehilangan Bola dalam Sepak Bola "
        "Menggunakan Graph Neural Network dan Spatiotemporal Tracking Data"
    )

    date_paragraph = doc.add_paragraph()
    date_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_paragraph.paragraph_format.space_before = Pt(18)
    date_run = date_paragraph.add_run("2 Oktober 2026")
    date_run.italic = True
    date_run.font.color.rgb = RGBColor.from_string(GRAY)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    core = doc.add_paragraph()
    core.paragraph_format.left_indent = Cm(0.8)
    core.paragraph_format.right_indent = Cm(0.8)
    lead = core.add_run("Inti penelitian. ")
    lead.bold = True
    lead.font.color.rgb = RGBColor.from_string(TEAL_DARK)
    core.add_run(
        "Setiap kehilangan bola diubah menjadi sequence graph pemain dan bola. Manusia memberi "
        "label apakah respons sesudah kehilangan bola benar-benar menunjukkan gegenpressing. "
        "Baseline dan temporal GNN kemudian belajar mendeteksi perilaku tersebut. Keberhasilan "
        "merebut bola kembali dan nilai VAEP dianalisis sebagai outcome terpisah, bukan sebagai "
        "pengganti label perilaku."
    )

    doc.add_heading("Tujuan dokumen", level=1)
    doc.add_paragraph(
        "Panduan ini menjelaskan alasan di balik setiap tahap, hubungan antarkomponen, bentuk "
        "input dan output, risiko metodologis, serta cara membaca hasil. Setelah membaca dokumen "
        "ini, alur penelitian seharusnya dapat dijelaskan kembali tanpa bergantung pada kode."
    )
    doc.add_page_break()


def add_document_map(doc: Document) -> None:
    doc.add_heading("Peta dokumen", level=1)
    rows = [
        ["1 sampai 3", "Apa yang diteliti, mengapa tracking diperlukan, dan bagaimana dua target dipisahkan"],
        ["4 sampai 6", "Bagaimana turnover menjadi episode valid, dianotasi, lalu dibagi per pertandingan"],
        ["7 sampai 9", "Bagaimana baseline dan temporal GNN dilatih serta dievaluasi"],
        ["10", "Bagaimana efektivitas dan VAEP ditempatkan secara metodologis"],
        ["11 sampai 13", "Status aktual, urutan kerja final, istilah penting, dan cara menjelaskan penelitian"],
    ]
    add_table(doc, ["Bagian", "Pertanyaan yang dijawab"], rows, [3.0, 13.0])

    doc.add_heading("Cara membaca alur", level=2)
    reading_steps = [
        "Pahami dulu unit analisis dan pemisahan behavior dari outcome.",
        "Ikuti perubahan data dari pertandingan menjadi episode, lalu menjadi graph.",
        "Lihat baseline dan GNN sebagai dua cara berbeda untuk membaca episode yang sama.",
        "Baca evaluasi sebagai pengujian pada pertandingan yang tidak dipakai untuk fitting.",
        "Tempatkan VAEP setelah deteksi stabil, bukan sebagai label deteksi.",
    ]
    for number, step in enumerate(reading_steps, start=1):
        add_number(doc, number, step)


def add_foundation_sections(doc: Document, pipeline_path: Path, matrix_path: Path) -> None:
    doc.add_heading("1 Pertanyaan penelitian dan unit analisis", level=1)
    doc.add_paragraph(
        "Penelitian ini tidak mencoba memberi label tetap kepada sebuah klub sebagai tim "
        "gegenpressing. Objek yang dinilai adalah satu situasi transisi setelah sebuah tim "
        "kehilangan penguasaan bola. Satu situasi dapat menunjukkan gegenpressing, sedangkan "
        "situasi lain dari tim yang sama dapat menunjukkan retreat atau reorganisasi."
    )
    add_lead_paragraph(
        doc,
        "Pertanyaan deteksi. ",
        "Apakah pola gerak kolektif pemain selama dua detik pertama setelah kehilangan bola "
        "menunjukkan tekanan segera yang dapat disebut gegenpressing?",
    )
    add_lead_paragraph(
        doc,
        "Pertanyaan efektivitas. ",
        "Jika gegenpressing terjadi, apakah tim berhasil memperoleh kembali penguasaan dengan "
        "cepat, seberapa lama prosesnya, dan bagaimana konsekuensi nilai permainan setelahnya?",
    )
    add_lead_paragraph(
        doc,
        "Unit analisis. ",
        "Satu episode transisi dengan titik acuan T0, yaitu frame pertama ketika kepemilikan "
        "bola berpindah dari tim kehilangan bola kepada lawan saat bola hidup.",
    )

    doc.add_heading("2 Gambaran besar pipeline", level=1)
    doc.add_paragraph(
        "Pipeline mengubah data mentah menjadi bukti penelitian secara bertahap. Setiap tahap "
        "memiliki output yang dapat diaudit. Model tidak langsung menerima pertandingan utuh; "
        "model menerima episode yang telah lolos pemeriksaan struktur dan memiliki label manusia."
    )
    add_picture(
        doc,
        pipeline_path,
        6.35,
        "Gambar 1. Alur penelitian VAEP-Track dari data sampai analisis efektivitas",
        "Diagram alur dari data IDSSE, deteksi turnover, pembentukan episode dan graph, anotasi manual, split pertandingan, baseline dan temporal GNN, hingga analisis outcome dan valuasi.",
    )

    doc.add_heading("3 Pemisahan behavior dan outcome", level=1)
    doc.add_paragraph(
        "Konsep terpenting dalam penelitian ini adalah membedakan apa yang dilakukan tim dari "
        "hasil yang terjadi. Gegenpressing adalah perilaku tekanan setelah kehilangan bola. "
        "Quick regain adalah outcome berupa penguasaan kembali dalam lima detik. Keduanya dapat "
        "berhubungan, tetapi tidak identik."
    )
    add_picture(
        doc,
        matrix_path,
        6.2,
        "Gambar 2. Empat kombinasi antara perilaku gegenpressing dan outcome quick regain",
        "Matriks dua kali dua yang memisahkan perilaku gegenpressing atau bukan gegenpressing dari outcome quick regain berhasil atau gagal.",
    )
    doc.add_paragraph(
        "Apabila quick regain langsung dijadikan label gegenpressing, model akan belajar hasil, "
        "bukan perilaku. Tim dapat menekan dengan benar tetapi gagal merebut bola. Sebaliknya, "
        "tim dapat merebut bola karena umpan buruk lawan tanpa melakukan tekanan kolektif. "
        "Karena itu quick regain disembunyikan selama anotasi perilaku dan baru ditampilkan pada "
        "tahap audit outcome."
    )
    distinction_rows = [
        ["is_gegenpressing", "Behavior", "Anotasi manusia dari visual T0 sampai T0+2 s", "Target model deteksi"],
        ["quick_regain_success", "Outcome", "Kepemilikan kembali dalam maksimum 5 s", "Analisis efektivitas"],
        ["regain_gap_seconds", "Outcome kontinu", "Selisih waktu T0 sampai regain", "Kecepatan hasil tekanan"],
        ["VAEP atau VAEP-inspired", "Nilai konsekuensi", "Perubahan probabilitas mencetak dan kebobolan atau proksi tervalidasi", "Valuasi akhir"],
    ]
    add_table(doc, ["Variabel", "Peran", "Sumber", "Digunakan untuk"], distinction_rows, [3.3, 3.0, 5.2, 4.5])


def add_data_sections(doc: Document, graph_path: Path, status: dict[str, int]) -> None:
    doc.add_page_break()
    doc.add_heading("4 Dari dataset menjadi kandidat transisi", level=1)
    doc.add_heading("4.1 Dua jenis data yang saling melengkapi", level=2)
    data_rows = [
        ["Tracking", "Posisi pemain dan bola pada 25 Hz, ball state, dan ball owning team", "Mendeteksi perubahan penguasaan dan membentuk pola spasial"],
        ["Event", "Aksi diskret, pemain, tim, dan konteks kejadian", "Memetakan identitas pemain ke tim dan memberi konteks pertandingan"],
    ]
    add_table(doc, ["Sumber", "Isi utama", "Peran penelitian"], data_rows, [3.0, 6.5, 6.5])
    doc.add_paragraph(
        "Tracking dipakai sebagai sumber utama perubahan penguasaan karena tersedia kontinu. "
        "Event tetap penting, tetapi tidak dijadikan satu-satunya sumber turnover karena jumlah "
        "event recovery terbatas dan struktur timestamp tidak selalu cukup untuk mendeteksi semua "
        "perubahan penguasaan."
    )

    doc.add_heading("4.2 Logika deteksi turnover", level=2)
    turnover_steps = [
        "Urutkan tracking berdasarkan period, timestamp, dan frame.",
        "Bandingkan ball_owning_team_id pada frame sekarang dengan frame sebelumnya.",
        "Tandai perubahan pemilik hanya ketika kedua ID tersedia dan bola berstatus alive.",
        "Simpan tim kehilangan bola, tim lawan, timestamp, frame, dan candidate_id.",
        "Cari apakah tim kehilangan bola memperoleh penguasaan kembali dalam lima detik.",
    ]
    for number, step in enumerate(turnover_steps, start=1):
        add_number(doc, number, step)

    quantity_rows = [
        ["Perubahan penguasaan awal", "2.847", "Semua perubahan yang terdeteksi sebelum filter bola hidup"],
        ["Kandidat defensive transition", "2.353", "Perubahan penguasaan saat bola hidup"],
        ["Quick regain dalam 5 detik", "1.105", "Outcome positif, sekitar 46,96 persen kandidat"],
        ["Episode strict-valid", "1.873", "Window lengkap dan struktur graph konsisten"],
        ["Queue anotasi", "264", "Sampel lintas tujuh pertandingan untuk label behavior"],
    ]
    add_table(doc, ["Tahap", "Jumlah", "Makna"], quantity_rows, [5.2, 2.6, 8.2])

    doc.add_heading("4.3 Mengapa tidak semua 1.873 episode dianotasi", level=2)
    doc.add_paragraph(
        "Anotasi visual membutuhkan waktu. Queue 264 dipilih secara reproducible dari episode "
        "strict-valid, tersebar pada tujuh pertandingan, diberi jarak waktu minimum, dan "
        "diseimbangkan menurut outcome quick regain untuk memastikan kedua jenis outcome terlihat "
        "selama pengembangan. Outcome dipakai untuk sampling, tetapi tidak ditampilkan kepada "
        "annotator ketika menentukan behavior."
    )
    add_lead_paragraph(
        doc,
        "Konsekuensi penting. ",
        "Proporsi label di queue bukan estimasi prevalensi alami gegenpressing di seluruh liga. "
        "Hasil penelitian harus dibaca sebagai evaluasi metode pada sampel terstruktur.",
    )

    doc.add_heading("5 Episode tracking dan graph spatiotemporal", level=1)
    doc.add_heading("5.1 Window episode", level=2)
    doc.add_paragraph(
        "Untuk graph, satu episode mengambil dua detik sebelum T0 sampai dua detik setelah T0. "
        "Pada frekuensi 25 Hz, kedua ujung waktu ikut dihitung sehingga terdapat 101 frame. "
        "Bagian sebelum T0 memberi konteks menuju kehilangan bola, sedangkan bagian setelah T0 "
        "menangkap respons tekanan. Keputusan anotasi behavior tetap berfokus pada T0 sampai T0+2 s."
    )
    graph_rows = [
        ["Frame per episode", "101", "Window -2,00 s sampai +2,00 s pada 25 Hz"],
        ["Node per frame", "23", "11 pemain tim kehilangan bola, 11 lawan, dan 1 bola"],
        ["Fitur per node", "6", "x, y, speed, is_ball, is_losing_team, is_opponent"],
        ["Edge per frame", "92", "Empat edge keluar ke tetangga spasial terdekat untuk tiap node"],
        ["Bentuk tensor", "101 x 23 x 6", "Sequence fitur node yang masuk ke temporal GNN"],
    ]
    add_table(doc, ["Komponen", "Ukuran", "Interpretasi"], graph_rows, [4.2, 3.0, 8.8])
    add_picture(
        doc,
        graph_path,
        6.45,
        "Gambar 3. Ilustrasi tiga frame dari sequence graph sepanjang 101 frame",
        "Tiga ilustrasi graph pada minus dua detik, saat kehilangan bola, dan plus dua detik; node mewakili pemain dan bola, sedangkan edge menghubungkan tetangga spasial terdekat.",
    )

    doc.add_heading("5.2 Mengapa graph cocok untuk sepak bola", level=2)
    add_bullet(doc, "Pemain dan bola secara alami dapat dipandang sebagai entitas atau node.")
    add_bullet(doc, "Jarak dan kedekatan antarentitas dapat direpresentasikan sebagai edge.")
    add_bullet(doc, "GCN dapat menggabungkan informasi tetangga sehingga relasi lokal tidak hilang.")
    add_bullet(doc, "Sequence frame mempertahankan perubahan relasi terhadap waktu.")
    add_bullet(doc, "Urutan node konsisten, sehingga pemain yang sama tidak berpindah identitas antarframe.")

    doc.add_heading("5.3 Syarat strict-valid", level=2)
    strict_rows = [
        ["Window lengkap", "Tepat 101 frame tersedia"],
        ["Frame kontinu", "frame_id bertambah satu tanpa celah"],
        ["Timestamp regular", "Jarak antarframe konsisten dengan 25 Hz"],
        ["Roster lengkap", "11 pemain melawan 11 pemain pada frame kehilangan bola"],
        ["Posisi valid", "Seluruh pemain dan bola memiliki koordinat valid pada window"],
    ]
    add_table(doc, ["Pemeriksaan", "Alasan"], strict_rows, [5.0, 11.0])

    doc.add_heading("6 Ground truth melalui anotasi manual", level=1)
    doc.add_heading("6.1 Definisi operasional", level=2)
    definition_rows = [
        ["1 Gegenpressing", "Sedikitnya satu pemain segera dan sengaja menutup pembawa bola, atau beberapa pemain menutup ruang dan opsi umpan di sekitar bola; tekanan tampak berkelanjutan."],
        ["0 Bukan", "Respons dominan adalah mundur atau reorganisasi, tidak ada tekanan segera, atau kedekatan hanya berasal dari bentuk pertahanan biasa."],
        ["-1 Ragu", "Bola udara, rebound, duel atau pembawa bola tidak jelas, atau bukti visual tidak cukup. Label ini tidak dipakai untuk training."],
    ]
    add_table(doc, ["Label", "Aturan keputusan"], definition_rows, [3.6, 12.4])

    doc.add_heading("6.2 Peran pressure cues", level=2)
    doc.add_paragraph(
        "Panel anotasi menampilkan jarak pemain ke bola, approach rate, jumlah presser, "
        "compactness, dan durasi tekanan. Cue tersebut membantu annotator melihat pola yang sulit "
        "ditangkap dari satu frame, tetapi tidak menghasilkan label otomatis. Keputusan akhir tetap "
        "berasal dari pembacaan visual seluruh sequence."
    )
    cue_rows = [
        ["Jarak minimum", "Apakah pemain tim kehilangan bola benar-benar mendekati area bola"],
        ["Approach rate", "Apakah jarak pemain ke bola berkurang dengan cepat"],
        ["Jumlah presser", "Apakah tekanan hanya individual atau melibatkan dukungan kolektif"],
        ["Compactness", "Apakah pemain sekitar bola merapat sebagai unit"],
        ["Durasi", "Apakah tekanan bertahan, bukan hanya kebetulan satu atau dua frame"],
    ]
    add_table(doc, ["Cue", "Pertanyaan yang dibantu"], cue_rows, [4.0, 12.0])

    doc.add_heading("6.3 Status anotasi saat ini", level=2)
    status_rows = [
        ["Total queue", status["total"], "Target yang harus diselesaikan"],
        ["Selesai", status["completed"], "Sudah memiliki label, confidence, dan annotator"],
        ["Gegenpressing", status["positive"], "Label behavior 1"],
        ["Bukan gegenpressing", status["negative"], "Label behavior 0"],
        ["Ragu", status["uncertain"], "Dikeluarkan dari training dan wajib memiliki catatan"],
        ["Belum dianotasi", status["remaining"], "Pekerjaan manual yang masih tersisa"],
    ]
    add_table(doc, ["Status", "Jumlah", "Makna"], status_rows, [5.0, 2.5, 8.5])
    doc.add_paragraph(
        "Quality gate memeriksa kelengkapan label, nilai confidence, catatan untuk label ragu, "
        "identitas annotator, keunikan candidate_id, keberadaan dua kelas pada setiap split, serta "
        "minimum contoh per kelas. Training final tidak dapat dimulai sebelum gate ini lulus."
    )


def add_model_sections(doc: Document) -> None:
    doc.add_page_break()
    doc.add_heading("7 Split data dan pencegahan leakage", level=1)
    doc.add_paragraph(
        "Frame dalam pertandingan yang sama sangat berkorelasi. Apabila episode dari satu "
        "pertandingan diacak ke train dan test, model dapat mengenali karakteristik pertandingan, "
        "tim, atau pola tracking yang sama. Nilai evaluasi kemudian tampak tinggi tanpa membuktikan "
        "kemampuan generalisasi ke pertandingan baru. Karena itu unit split adalah pertandingan."
    )
    split_rows = [
        ["Train", "J03WMX, J03WN1, J03WOH, J03WOY, J03WR9", "Fitting parameter model"],
        ["Validation", "J03WQQ", "Early stopping dan pemilihan threshold"],
        ["Test", "J03WPY", "Evaluasi akhir sekali setelah keputusan model dikunci"],
    ]
    add_table(doc, ["Split", "Pertandingan", "Fungsi"], split_rows, [3.0, 8.2, 4.8])
    add_lead_paragraph(
        doc,
        "Aturan keras. ",
        "Threshold tidak boleh dipilih dari test, hyperparameter tidak boleh disesuaikan setelah "
        "melihat test, dan label quick regain tidak boleh masuk sebagai fitur deteksi.",
    )

    doc.add_heading("8 Baseline pembanding", level=1)
    doc.add_paragraph(
        "Baseline menjawab pertanyaan: apakah temporal GNN benar-benar memberi manfaat dibanding "
        "fitur tekanan yang sudah diringkas? Tanpa baseline, model yang kompleks tidak memiliki "
        "pembanding yang adil. Dua baseline digunakan, yaitu logistic regression untuk hubungan "
        "linear yang mudah ditafsirkan dan XGBoost untuk hubungan non-linear berbasis pohon."
    )
    baseline_rows = [
        ["Intensitas tekanan", "max_total_pressers, max_direct_pressers, max_approaching_pressers"],
        ["Durasi", "pressure_duration_s, collective_pressure_duration_s"],
        ["Keberlanjutan", "sustained_pressure_cue, sustained_collective_cue"],
        ["Kedekatan dan gerak", "minimum_losing_distance_m, maximum_approach_rate_mps"],
        ["Kepadatan lokal", "max_losing_players_within_10m, mean_local_compactness_m"],
        ["Perubahan bentuk", "team_stretch_change_m"],
    ]
    add_table(doc, ["Kelompok", "Fitur"], baseline_rows, [4.2, 11.8])
    doc.add_paragraph(
        "Nilai kosong diimputasi dengan median. Logistic regression menerima standardisasi dan "
        "class weight seimbang. XGBoost menerima sample weight seimbang. Kedua model hanya di-fit "
        "pada train, sedangkan threshold klasifikasi dipilih pada validation."
    )

    doc.add_heading("9 Temporal Graph Neural Network", level=1)
    doc.add_heading("9.1 Aliran komputasi", level=2)
    architecture_rows = [
        ["Input", "101 x 23 x 6", "Sequence node features untuk satu episode"],
        ["GCN 1", "6 ke 32", "Menggabungkan informasi dari tetangga spasial"],
        ["GCN 2", "32 ke 32", "Membentuk representasi graph yang lebih kaya"],
        ["Layer normalization", "32", "Menstabilkan distribusi hidden representation"],
        ["Masked mean pooling", "23 node ke 1 frame", "Menghasilkan embedding 32 dimensi per frame"],
        ["GRU", "101 frame ke 1 episode", "Merangkum evolusi tekanan terhadap waktu"],
        ["Linear classifier", "32 ke 2 logits", "Skor kelas bukan gegenpressing dan gegenpressing"],
    ]
    add_table(doc, ["Tahap", "Bentuk", "Fungsi"], architecture_rows, [4.0, 4.0, 8.0])

    doc.add_heading("9.2 Preprocessing dan training", level=2)
    add_bullet(doc, "Fitur kontinu x, y, dan speed dinormalisasi memakai mean dan standard deviation train saja.")
    add_bullet(doc, "Indikator is_ball, is_losing_team, dan is_opponent tetap biner.")
    add_bullet(doc, "Class-weighted cross entropy mengurangi dominasi kelas mayoritas.")
    add_bullet(doc, "AdamW memperbarui parameter model; validation loss menentukan early stopping.")
    add_bullet(doc, "State terbaik disimpan, lalu threshold dipilih dari validation menggunakan F1 pada kurva precision-recall.")
    add_bullet(doc, "Test hanya dievaluasi setelah model dan threshold terkunci.")

    doc.add_heading("9.3 Apa yang dipelajari model", level=2)
    doc.add_paragraph(
        "GCN tidak diberi aturan eksplisit bahwa tiga pemain dekat bola pasti merupakan "
        "gegenpressing. Model belajar pola kombinasi: posisi relatif, kedekatan graph, kecepatan, "
        "identitas tim, serta perubahan pola selama 101 frame. GRU memungkinkan model membedakan "
        "kedekatan statis dari gerakan tekanan yang berkembang setelah kehilangan bola."
    )
    add_lead_paragraph(
        doc,
        "Batas interpretasi. ",
        "Model dapat memberi probabilitas gegenpressing, tetapi probabilitas tinggi bukan bukti "
        "kausal bahwa tekanan menyebabkan regain. Hubungan efektivitas dianalisis terpisah.",
    )


def add_evaluation_and_value_sections(doc: Document) -> None:
    doc.add_heading("10 Evaluasi model dan cara membacanya", level=1)
    metrics_rows = [
        ["Precision", "Dari semua prediksi gegenpressing, berapa yang benar", "Penting ketika false positive harus dibatasi"],
        ["Recall", "Dari semua gegenpressing aktual, berapa yang ditemukan", "Penting agar pola tekanan tidak banyak terlewat"],
        ["F1", "Rata-rata harmonik precision dan recall", "Ringkasan keseimbangan dua metrik"],
        ["PR-AUC", "Kualitas ranking pada kurva precision-recall", "Lebih informatif saat kelas tidak seimbang"],
        ["ROC-AUC", "Kemampuan ranking positif di atas negatif", "Mudah dibandingkan tetapi dapat optimistis pada imbalance"],
        ["Confusion matrix", "Jumlah TP, FP, TN, dan FN", "Menunjukkan jenis kesalahan secara konkret"],
    ]
    add_table(doc, ["Metrik", "Makna", "Cara menggunakan"], metrics_rows, [3.0, 7.0, 6.0])
    doc.add_paragraph(
        "Metrik dihitung per split dan per pertandingan. Set kandidat harus identik untuk logistic "
        "regression, XGBoost, dan temporal GNN. Pipeline menolak prediksi jika candidate_id, label, "
        "split, pertandingan, threshold, probabilitas, atau y_pred tidak konsisten."
    )

    doc.add_heading("10.1 Mengapa hasil smoke bukan hasil final", level=2)
    doc.add_paragraph(
        "Smoke test hanya membuktikan bahwa data dapat bergerak dari CSV sampai model, checkpoint, "
        "prediksi, dan tabel evaluasi. Saat ini hanya 26 label biner yang usable, termasuk tiga "
        "sampel pada test. Nilai F1 atau AUC dari ukuran tersebut sangat tidak stabil dan tidak "
        "boleh dimasukkan sebagai kesimpulan performa penelitian."
    )
    add_lead_paragraph(
        doc,
        "Kapan metrik boleh dilaporkan. ",
        "Setelah 264 sampel selesai dianotasi, review queue diaudit, semua quality gate lulus, "
        "runner final selesai, dan artefak final lolos verifikasi checksum.",
    )

    doc.add_heading("11 Dari deteksi menuju valuasi efektivitas", level=1)
    doc.add_heading("11.1 Tiga lapisan jawaban", level=2)
    layers = [
        ["Lapisan 1 Deteksi", "Apakah gegenpressing terjadi?", "Probabilitas dan kelas is_gegenpressing"],
        ["Lapisan 2 Outcome", "Apakah bola direbut kembali dengan cepat?", "quick_regain_success dan regain_gap_seconds"],
        ["Lapisan 3 Nilai", "Apakah konsekuensi setelahnya menguntungkan?", "VAEP kanonik atau skor efektivitas yang didefinisikan transparan"],
    ]
    add_table(doc, ["Lapisan", "Pertanyaan", "Output"], layers, [4.0, 6.0, 6.0])

    doc.add_heading("11.2 VAEP kanonik", level=2)
    doc.add_paragraph(
        "VAEP menilai sebuah aksi dari perubahan probabilitas tim mencetak gol dan kebobolan "
        "antara keadaan sebelum dan sesudah aksi. Implementasi kanonik memerlukan pemetaan event "
        "IDSSE ke action schema yang konsisten, urutan aksi yang dapat divalidasi, serta model "
        "probabilitas scoring dan conceding. Nama VAEP kanonik hanya boleh digunakan jika seluruh "
        "pemetaan tersebut berhasil diaudit."
    )

    doc.add_heading("11.3 Alternatif VAEP-inspired", level=2)
    doc.add_paragraph(
        "Apabila event IDSSE tidak dapat dipetakan secara lengkap, penelitian masih dapat menilai "
        "efektivitas melalui skor yang menggabungkan regain, waktu menuju regain, lokasi regain, "
        "dan konsekuensi penguasaan berikutnya. Namun skor tersebut harus diberi nama "
        "VAEP-inspired effectiveness score, dengan rumus dan keterbatasan dijelaskan. Ia tidak "
        "boleh disajikan seolah-olah identik dengan VAEP Decroos dan kolega."
    )
    decision_rows = [
        ["Pemetaan action schema tervalidasi", "Gunakan VAEP kanonik", "Jelaskan model scoring dan conceding serta state sebelum dan sesudah aksi"],
        ["Pemetaan hanya sebagian", "Gunakan VAEP-inspired", "Definisikan komponen, bobot, sensitivitas, dan keterbatasan"],
        ["Outcome belum stabil", "Tunda valuasi", "Selesaikan dan evaluasi deteksi lebih dahulu"],
    ]
    add_table(doc, ["Kondisi", "Keputusan", "Kewajiban laporan"], decision_rows, [5.0, 4.0, 7.0])


def add_status_and_explanation_sections(doc: Document, status: dict[str, int]) -> None:
    doc.add_page_break()
    doc.add_heading("12 Status penelitian dan urutan menuju training final", level=1)
    status_rows = [
        ["Dataset tersedia dan terbaca", "Selesai", "Tujuh pertandingan event dan tracking"],
        ["Kuantitas turnover dan episode", "Selesai", "2.353 kandidat aktif dan 1.873 strict-valid"],
        ["Graph cache", "Selesai", "264 sample dengan 101 frame, 23 node, 6 fitur, dan 92 edge"],
        ["Pilot baseline dan temporal GNN", "Selesai sebagai smoke test", "Pipeline dan GPU terverifikasi; bukan hasil final"],
        ["Anotasi penuh", "Belum selesai", f"{status['completed']} dari {status['total']} selesai; {status['remaining']} tersisa"],
        ["Audit label penuh", "Menunggu anotasi", "Notebook audit dan blinded review queue sudah tersedia"],
        ["Training dan evaluasi final", "Menunggu quality gate", "Runner otomatis tersedia dan tidak dapat melewati gate"],
        ["Keputusan valuasi", "Belum final", "Uji kompatibilitas VAEP kanonik setelah deteksi stabil"],
    ]
    add_table(doc, ["Komponen", "Status", "Bukti atau kondisi"], status_rows, [5.3, 4.0, 6.7])

    doc.add_heading("12.1 Urutan kerja yang benar", level=2)
    final_steps = [
        "Selesaikan seluruh queue pada notebook 08 tanpa melihat quick regain sebagai dasar keputusan.",
        "Jalankan notebook 13 dan tinjau ulang label ragu serta confidence rendah dari blinded review queue.",
        "Pastikan setiap split memiliki kedua kelas dan minimum jumlah per kelas yang disyaratkan.",
        "Jalankan final readiness check; lanjutkan hanya ketika seluruh status bernilai True.",
        "Latih logistic regression dan XGBoost sebagai baseline menggunakan train split.",
        "Latih temporal GNN dengan early stopping pada validation.",
        "Kunci threshold dari validation dan evaluasi test tanpa tuning tambahan.",
        "Bandingkan model pada kandidat yang identik, lalu interpretasikan kesalahan per pertandingan.",
        "Audit artefak, metadata, environment, dan checksum sebelum hasil diberi status final.",
        "Lanjutkan ke analisis outcome dan putuskan VAEP kanonik atau VAEP-inspired.",
    ]
    for number, step in enumerate(final_steps, start=1):
        add_number(doc, number, step)

    doc.add_heading("12.2 Artefak final yang dihasilkan", level=2)
    artifacts = [
        ["Frozen data", "frozen_annotations.csv dan frozen_model_manifest.csv"],
        ["Audit anotasi", "annotation_audit_summary.csv, review queue, dan audit checks"],
        ["Baseline", "Dua model, metadata, metrics, dan predictions"],
        ["Temporal GNN", "Checkpoint, normalizer train-only, history, metrics, dan predictions"],
        ["Evaluasi", "Combined predictions, split metrics, dan match metrics"],
        ["Reproduksibilitas", "Environment, git state, random seed, dan SHA-256 checksum"],
        ["Ringkasan", "training_summary.md dengan penanda hasil final"],
    ]
    add_table(doc, ["Kelompok", "Isi"], artifacts, [4.2, 11.8])

    doc.add_heading("13 Cara menjelaskan penelitian dengan sederhana", level=1)
    doc.add_heading("13.1 Versi satu menit", level=2)
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.6)
    paragraph.paragraph_format.right_indent = Cm(0.6)
    paragraph.add_run(
        "Penelitian saya mengubah setiap situasi kehilangan bola menjadi rangkaian graph selama "
        "empat detik. Pemain dan bola menjadi node, sedangkan kedekatan spasial menjadi edge. "
        "Saya memberi label manual apakah respons dua detik setelah kehilangan bola merupakan "
        "gegenpressing. Logistic regression dan XGBoost menjadi baseline, sedangkan GCN dan GRU "
        "mempelajari pola spasial dan temporal. Data dibagi per pertandingan untuk mencegah "
        "leakage. Setelah deteksi stabil, quick regain dan VAEP digunakan untuk menilai efektivitas, "
        "bukan untuk menentukan label gegenpressing. Karena dataset hanya tujuh pertandingan, "
        "kesimpulan dibatasi sebagai proof of concept pada IDSSE."
    ).italic = True

    doc.add_heading("13.2 Pertanyaan yang sering muncul", level=2)
    faq_rows = [
        ["Mengapa tidak memakai quick regain sebagai label?", "Karena quick regain adalah hasil. Perilaku menekan dapat berhasil atau gagal, dan regain dapat terjadi tanpa gegenpressing."],
        ["Mengapa memakai GNN?", "Karena objek utama adalah relasi antar-pemain dan bola yang berubah dari frame ke frame."],
        ["Mengapa masih perlu baseline?", "Agar manfaat representasi graph dapat dibandingkan dengan fitur tekanan yang lebih sederhana."],
        ["Mengapa split per pertandingan?", "Untuk mencegah frame dan pola pertandingan yang sangat mirip masuk ke train dan test sekaligus."],
        ["Apakah 1.873 episode berarti semua siap training?", "Tidak. Itu hanya valid secara struktur. Model deteksi tetap memerlukan label behavior manual pada queue 264."],
        ["Apakah hasil dapat digeneralisasi ke semua liga?", "Belum. Tujuh pertandingan cukup untuk proof of concept, bukan klaim universal."],
        ["Kapan istilah VAEP boleh dipakai?", "Ketika event dapat dipetakan dan model state-value sesuai definisi VAEP kanonik telah divalidasi."],
    ]
    add_table(doc, ["Pertanyaan", "Jawaban inti"], faq_rows, [6.0, 10.0])

    doc.add_heading("13.3 Pernyataan yang boleh dan tidak boleh dibuat", level=2)
    claim_rows = [
        ["Boleh", "Pipeline dapat membentuk graph temporal secara konsisten dan membandingkan baseline dengan temporal GNN pada split pertandingan."],
        ["Boleh", "Hasil final berlaku sebagai evaluasi metode pada sampel IDSSE yang digunakan."],
        ["Belum boleh", "Temporal GNN terbukti lebih baik sebelum training final dan evaluasi test selesai."],
        ["Belum boleh", "Semua quick regain merupakan gegenpressing atau semua gegenpressing menghasilkan quick regain."],
        ["Belum boleh", "Hasil tujuh pertandingan mewakili seluruh sepak bola profesional."],
        ["Belum boleh", "Skor disebut VAEP kanonik sebelum pemetaan action schema tervalidasi."],
    ]
    add_table(doc, ["Status", "Pernyataan"], claim_rows, [3.0, 13.0])


def add_glossary_and_references(doc: Document) -> None:
    doc.add_heading("Glosarium", level=1)
    glossary = [
        ["T0", "Frame awal perubahan penguasaan yang menjadi titik acuan episode"],
        ["Defensive transition", "Fase ketika sebuah tim baru kehilangan penguasaan dan berpindah ke bertahan"],
        ["Gegenpressing", "Tekanan segera dan terkoordinasi setelah kehilangan bola"],
        ["Quick regain", "Penguasaan kembali oleh tim kehilangan bola dalam jendela maksimal lima detik"],
        ["Node", "Pemain atau bola dalam graph"],
        ["Edge", "Relasi spasial terarah ke tetangga terdekat"],
        ["GCN", "Graph Convolutional Network yang mengagregasi informasi node tetangga"],
        ["GRU", "Recurrent neural network yang merangkum perubahan embedding sepanjang waktu"],
        ["Data leakage", "Informasi dari validation atau test memengaruhi fitting atau keputusan model"],
        ["Threshold", "Batas probabilitas untuk mengubah skor model menjadi kelas 0 atau 1"],
        ["Strict-valid", "Episode yang memenuhi seluruh syarat struktur sequence dan graph"],
        ["Smoke test", "Uji integrasi pipeline, bukan hasil performa penelitian"],
        ["VAEP", "Kerangka valuasi aksi berdasarkan perubahan probabilitas mencetak dan kebobolan"],
    ]
    add_table(doc, ["Istilah", "Arti dalam penelitian"], glossary, [4.2, 11.8])

    doc.add_heading("Peta notebook", level=1)
    notebooks = [
        ["01 sampai 03", "Audit data, event, turnover, dan kuantitas dataset"],
        ["04", "Proof of concept satu graph sequence dan forward pass"],
        ["05", "Audit seluruh kandidat episode"],
        ["06", "Pilot anotasi manual"],
        ["07", "Readiness dan split per pertandingan"],
        ["08", "Anotasi penuh 264 transisi"],
        ["09", "Ekstraksi 12 fitur baseline"],
        ["10", "Training baseline smoke atau final sesuai gate"],
        ["11", "Graph cache dan temporal GNN"],
        ["12", "Evaluasi gabungan dan match-level"],
        ["13", "Audit kualitas anotasi dan blinded review queue"],
    ]
    add_table(doc, ["Notebook", "Fungsi"], notebooks, [3.2, 12.8])

    doc.add_heading("Referensi utama", level=1)
    references = [
        "Bassek, M., Rein, R., Weber, H., dan Memmert, D. (2025). An integrated dataset of spatiotemporal and event data in elite soccer. Scientific Data, 12, 195. https://doi.org/10.1038/s41597-025-04505-y",
        "Bauer, P., dan Anzer, G. (2021). Data-driven detection of counterpressing in professional football. Data Mining and Knowledge Discovery, 35, 2009-2049. https://doi.org/10.1007/s10618-021-00763-7",
        "Decroos, T., Bransen, L., Van Haaren, J., dan Davis, J. (2019). Actions Speak Louder Than Goals: Valuing Player Actions in Soccer. Proceedings of ACM SIGKDD. https://doi.org/10.1145/3292500.3330758",
        "Bekkers, J., dan Sahasrabudhe, A. (2024). A Graph Neural Network deep-dive into successful counterattacks. arXiv:2411.17450.",
    ]
    for reference in references:
        paragraph = doc.add_paragraph(reference)
        paragraph.paragraph_format.left_indent = Cm(0.7)
        paragraph.paragraph_format.first_line_indent = Cm(-0.7)
        paragraph.paragraph_format.space_after = Pt(4)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    pipeline_path = ASSET_DIR / "pipeline.png"
    matrix_path = ASSET_DIR / "label_matrix.png"
    graph_path = ASSET_DIR / "graph_sequence.png"
    create_pipeline_figure(pipeline_path)
    create_label_matrix(matrix_path)
    create_graph_figure(graph_path)

    annotations = pd.read_csv(PROCESSED / "gegenpressing_annotation_manifest.csv")
    labels = pd.to_numeric(annotations["is_gegenpressing"], errors="coerce")
    status = {
        "total": int(len(annotations)),
        "completed": int(labels.notna().sum()),
        "remaining": int(labels.isna().sum()),
        "positive": int(labels.eq(1).sum()),
        "negative": int(labels.eq(0).sum()),
        "uncertain": int(labels.eq(-1).sum()),
    }

    doc = Document()
    configure_document(doc)
    add_cover(doc)
    add_document_map(doc)
    add_foundation_sections(doc, pipeline_path, matrix_path)
    add_data_sections(doc, graph_path, status)
    add_model_sections(doc)
    add_evaluation_and_value_sections(doc)
    add_status_and_explanation_sections(doc, status)
    add_glossary_and_references(doc)

    properties = doc.core_properties
    properties.title = "Panduan Alur Penelitian VAEP Track"
    properties.subject = "Penjelasan konseptual pipeline IDSSE, gegenpressing, temporal GNN, evaluasi, dan valuasi"
    properties.author = "VAEP-Track"
    properties.keywords = "gegenpressing, IDSSE, tracking, graph neural network, VAEP"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
