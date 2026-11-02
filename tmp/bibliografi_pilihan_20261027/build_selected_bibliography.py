from pathlib import Path
import json
import unicodedata

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT


root = Path(r"C:\VAEP-Track")
records = json.loads((root / "tmp/bibliografi_gabungan_20261026/selection.json").read_text(encoding="utf-8"))
by_title = {row["title"].lower(): row for row in records}

main_titles = [
    "An integrated dataset of spatiotemporal and event data in elite soccer",
    "Data-driven detection of counterpressing in professional football: A supervised machine learning task based on synchronized positional and event data with expert-based feature extraction",
    "The success factors of rest defense in soccer - A mixed-methods approach of expert interviews, tracking data, and machine learning",
    "A rule-based approach to classify counterpressing - analysis of its risks and relationship with rest defence",
    "TacticAI: An AI assistant for football tactics",
]
support_titles = [
    "A graph neural network deep-dive into successful counterattacks",
    "Actions speak louder than goals: Valuing player actions in soccer",
    "Graph neural networks to predict sports outcomes",
    "Graph neural networks: A review of methods and applications",
]
selected = [by_title[title.lower()] for title in main_titles + support_titles]
additional_records = json.loads((root / "tmp/bibliografi_gabungan_20261027/selected.json").read_text(encoding="utf-8"))
new_titles = {
    "visually-supported topic modeling for understanding behavioral patterns from spatio-temporal events",
    "using temporal convolutional networks to estimate ball possession in soccer games",
    "a spatiotemporal graph transformer network for real-time ball trajectory monitoring and prediction in dynamic sports environments",
    "shape graphs and the instantaneous inference of tactical positions in soccer",
}
selected.extend(row for row in additional_records if row["title"].lower() in new_titles)
assert len(selected) == 13
assert len({x["doi"] for x in selected}) == 13
selected.sort(key=lambda x: unicodedata.normalize("NFKD", x["author"]).casefold())

output = root / "docs/jurnalreferensi/Draf_Daftar_Pustaka_14_PDF_2026-10-27.docx"
doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(.78)
section.bottom_margin = Inches(.72)
section.left_margin = Inches(.9)
section.right_margin = Inches(.9)

for name in ["Normal", "Title", "Heading 1", "Heading 2"]:
    style = doc.styles[name]
    style.font.name = "Calibri"
    style.font.color.rgb = RGBColor(0, 0, 0)
normal = doc.styles["Normal"]
normal.font.size = Pt(10.5)
normal.paragraph_format.line_spacing = 1.0
normal.paragraph_format.space_after = Pt(6)
for name, size in [("Title", 20), ("Heading 1", 13), ("Heading 2", 11.5)]:
    style = doc.styles[name]
    style.font.size = Pt(size)
    style.font.bold = True
    style.paragraph_format.keep_with_next = True
    style.paragraph_format.space_before = Pt(12 if name != "Title" else 0)
    style.paragraph_format.space_after = Pt(6)
for border in doc.styles.element.xpath(".//w:pBdr"):
    border.getparent().remove(border)


def hyperlink(paragraph, label, url):
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True))
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "175A80")
    properties.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(underline)
    run.append(properties)
    text = OxmlElement("w:t")
    text.text = label
    run.append(text)
    link.append(run)
    paragraph._p.append(link)


def author_list(raw):
    names = []
    for part in raw.split(" and "):
        family, given = part.split(",", 1)
        initials = " ".join(piece[0] + "." for piece in given.strip().split() if piece)
        names.append(f"{family.strip()}, {initials}")
    if len(names) > 20:
        return ", ".join(names[:19]) + ", … " + names[-1]
    if len(names) > 1:
        return ", ".join(names[:-1]) + ", & " + names[-1]
    return names[0]


def add_reference(row, category):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(.35)
    paragraph.paragraph_format.first_line_indent = Inches(-.35)
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.keep_together = True
    title = row["title"].replace(" - ", " – ")
    if row["doi"] == "10.1007/s10618-021-00763-7":
        title = "Data-driven detection of counterpressing in professional football: A supervised machine learning task based on synchronized positional and event data with expert-based feature extraction"
    if row["doi"] == "10.1016/j.cag.2025.104245":
        title = "Visually-supported topic modeling for understanding behavioral patterns from spatio–temporal events"
    paragraph.add_run(f"{author_list(row['author'])} ({row['year']}). ")
    title_run = paragraph.add_run(title)
    title_run.italic = category == "preprint"
    if category != "preprint":
        paragraph.add_run(". ")
    if category == "journal":
        paragraph.add_run(f"{row['journal']}, {row['volume']}").italic = True
        issue = {
            "10.1007/s10618-021-00763-7": "5",
            "10.52082/jssm.2023.707": "4",
            "10.1080/24748668.2025.2473799": "1",
            "10.1038/s41467-024-45965-x": "1",
        }.get(row["doi"])
        if issue:
            paragraph.add_run(f"({issue})")
        pages = row["pages"].replace("--", "–")
        if row["doi"].startswith("10.1038/") or row["doi"] in {"10.1016/j.eswa.2023.119780", "10.1016/j.cag.2025.104245"}:
            pages = "Article " + pages
        paragraph.add_run(f", {pages}. ")
    elif category == "conference":
        paragraph.add_run("In ")
        paragraph.add_run(row["journal"]).italic = True
        paragraph.add_run(f" (pp. {row['pages'].replace('--', '–')}). ")
        paragraph.add_run("Association for Computing Machinery. " if row["doi"].startswith("10.1145/") else "IEEE. ")
    elif category == "preprint":
        paragraph.add_run(" [Preprint]. arXiv. ")
    elif category == "older_journal":
        paragraph.add_run(f"{row['journal']}, {row['volume']}").italic = True
        paragraph.add_run(f", {row['pages'].replace('--', '–')}. ")
    url = "https://arxiv.org/abs/2411.17450" if category == "preprint" else "https://doi.org/" + row["doi"]
    hyperlink(paragraph, url, url)


header = section.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
run = header.add_run("VAEP-TRACK  |  DRAF ARTIKEL JURNAL")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(100, 100, 100)
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run("Draf daftar pustaka  •  ")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(100, 100, 100)
field = OxmlElement("w:fldSimple")
field.set(qn("w:instr"), "PAGE")
footer._p.append(field)

doc.add_paragraph("Daftar Pustaka", style="Title")
for row in selected:
    if row["title"] == "A graph neural network deep-dive into successful counterattacks":
        category = "preprint"
    elif row["doi"] in {"10.1145/3292500.3330758", "10.1109/BigData52589.2021.9671833"}:
        category = "conference"
    else:
        category = "journal"
    add_reference(row, category)

doc.core_properties.title = "Draf Daftar Pustaka VAEP Track dari Sepuluh PDF Pilihan"
doc.core_properties.subject = "Daftar pustaka seluruh tiga belas karya unik dari empat belas PDF pilihan"
doc.core_properties.author = ""
doc.save(output)
print(json.dumps({"output": str(output), "pdf_count": 14, "bibliography_entries": len(selected)}, ensure_ascii=False))
