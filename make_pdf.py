from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors

from pathlib import Path


def md_to_paragraphs(md_text: str):
    """Very small Markdown-to-Paragraph converter (headers + code fences stripped)."""
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    title = styles["Heading1"]
    h2 = styles["Heading2"]
    h3 = styles["Heading3"]

    lines = md_text.splitlines()
    story = []
    in_code = False
    code_buffer = []

    def flush_code():
        if code_buffer:
            # Render code as a monospaced paragraph block
            code_text = "\n".join(code_buffer)
            p = Paragraph(f"<font face='Courier'>{code_text.replace('<','&lt;').replace('>','&gt;')}</font>", body)
            story.append(p)
            story.append(Spacer(1, 0.15 * inch))
            code_buffer.clear()

    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            if not in_code:
                flush_code()
            continue
        if in_code:
            code_buffer.append(line)
            continue
        if line.startswith("## "):
            story.append(Paragraph(line[3:], title))
            story.append(Spacer(1, 0.12 * inch))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], h2))
            story.append(Spacer(1, 0.08 * inch))
        elif line.startswith("- "):
            story.append(Paragraph(line, body))
        else:
            story.append(Paragraph(line, body))
        story.append(Spacer(1, 0.06 * inch))
    flush_code()
    return story


def build_pdf(md_path: Path, pdf_path: Path):
    text = md_path.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER, rightMargin=54, leftMargin=54, topMargin=60, bottomMargin=60)
    story = md_to_paragraphs(text)
    doc.build(story)
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    md_file = Path("PYTHON_BEGINNER_GUIDE.md")
    out_file = Path("PYTHON_BEGINNER_GUIDE.pdf")
    if not md_file.exists():
        raise SystemExit(f"Missing {md_file}")
    build_pdf(md_file, out_file)
