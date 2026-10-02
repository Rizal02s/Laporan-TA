# Template Contract for Proposal Judul VAEP Track

## Reference

- Source: `C:\Users\rizal\OneDrive\Documents\Laporan PKL & TA\Laporan_Document_TA\Proposal_VAEP-Track.docx`
- SHA-256: `2C1707FABBAF17F06D41C9205DB05E2F2C2BF36EDCAD9B9AC53117041A97FDC4`
- Source size: 23,266 bytes
- Pages: 4
- Sections: 1
- Reference render: `C:\VAEP-Track\docs\.proposal_judul_work\reference-render-word`
- Style evidence: `C:\VAEP-Track\docs\.proposal_judul_work\template-style-evidence.json`

## Page System

- One portrait A4 section, 8.27 x 11.69 inches.
- Margins: left 0.98 in, right 0.79 in, top 0.79 in, bottom 0.79 in.
- No visible header or footer, no page number, no first-page variation, and no columns.
- Continuous content flow with automatic page breaks; no manual section break.

## Typography

- Body uses the document Normal style with direct paragraph formatting where the source applies it.
- Main title: Normal style, 15 pt, bold, centered, 10 pt after.
- Heading 1: 14 pt, bold, dark blue `#1F4E79`, 16 pt before, 8 pt after, with the source's thin blue bottom rule.
- Body paragraphs: justified, 1.15 line spacing, 8 pt after.
- List paragraphs: justified, 1.15 line spacing, 5 pt after, source bullet and hanging-indent behavior preserved.
- Bold lead-ins within body and list items identify the role of each paragraph without creating new heading levels.

## Tables

- Table 1 is a two-row, five-column process flow with widths approximately 1.25, 1.32, 1.32, 0.97, and 1.25 inches.
- Table 2 is a two-column dataset summary with widths approximately 1.81 and 4.72 inches.
- Table 3 is a three-column comparison with widths approximately 1.53, 2.50, and 2.50 inches.
- All tables use visible black borders, dark blue `#1F4E79` header fill, white bold header text, and alternating white/pale-blue body rows.
- Header rows repeat when a table spans pages. Rows may expand and must not split across pages.

## Components and Content Flow

1. Centered research title.
2. Judul Penelitian.
3. Latar Belakang dan Gambaran Metode, followed by the five-step flow table.
4. Dataset yang Digunakan, followed by the dataset summary table.
5. Keterkaitan dengan Penelitian Bauer dan Anzer, followed by the comparison table.
6. Rencana Metodologi Awal as a bulleted sequence.
7. Batasan Awal as bullets.
8. Output yang Diharapkan as bullets.
9. Referensi Utama as numbered prose entries.

## Slot Map

- `word/document.xml` paragraph 0: rewrite with the recommended final title.
- Body paragraph 1 / Heading 1: preserve wording and style.
- Body paragraph 2: rewrite title statement, preserving bold project-name lead-in.
- Body paragraphs 3, 7, 10, 13, 23, 27, 33: preserve section purposes and Heading 1 formatting; wording may be refined while retaining numbering.
- Body paragraphs 4 to 6: rewrite background, research idea, and research flow using updated methodology.
- Table 0: rewrite process-stage labels and descriptions; preserve structure and style.
- Body paragraphs 8 to 9: rewrite dataset description and feasibility statement with verified project counts.
- Table 1: update project audit quantities and current working status; preserve row count and geometry.
- Body paragraphs 11 to 12: rewrite literature relation and research contribution.
- Table 2: update comparison while preserving 8 x 3 structure.
- Body paragraphs 14 to 22: rewrite nine methodology bullets in the same order and capacity.
- Body paragraphs 24 to 25: rewrite two limitation bullets.
- Body paragraphs 28 to 32: rewrite five expected outputs.
- Body paragraphs 34 to 38: preserve the five reference slots and correct encoding or wording where necessary.
- Empty paragraph 26: preserve as spacing.

## Package Preservation

- Editable: `word/document.xml` and `docProps/core.xml`.
- Preserve-only: `[Content_Types].xml`, `_rels/.rels`, `word/_rels/document.xml.rels`, `word/theme/theme1.xml`, `word/settings.xml`, `word/numbering.xml`, `word/styles.xml`, `word/webSettings.xml`, `word/fontTable.xml`, and `docProps/app.xml`.
- The reference contains no images, fields, footnotes, endnotes, content controls, headers, or footers.

## Fidelity Gates

- Reference must retain its recorded SHA-256.
- Final document must remain one A4 portrait section with the original margins.
- The eight blue Heading 1 sections, three table patterns, body typography, bullet rhythm, and source-derived page character must remain recognizable.
- No clipped text, split rows, orphaned headings, broken hyperlinks, or unexplained blank pages.
- Content changes are expected; movement of untouched styles, numbering, theme, page geometry, and package relationships is not.
