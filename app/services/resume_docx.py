"""Single-column A4 resume export, generated in memory without storing private data."""

from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

from app.schemas import ResumeContent


def export_resume_docx(content: ResumeContent) -> bytes:
    """Export validated saved content; final pagination depends on Word/WPS fonts."""
    document = Document()
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = section.bottom_margin = Mm(15)
    section.left_margin = section.right_margin = Mm(15)

    normal = document.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.1
    normal.paragraph_format.keep_together = True

    def heading(label: str) -> None:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.keep_with_next = True
        run = paragraph.add_run(label)
        run.bold = True
        run.font.name = "黑体"
        run.font.size = Pt(11)
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "黑体")

    title = document.add_paragraph()
    title.paragraph_format.keep_with_next = True
    run = title.add_run(content.name)
    run.bold = True
    run.font.size = Pt(18)
    contact = " | ".join(value for value in (content.phone, content.email) if value)
    if contact:
        document.add_paragraph(contact)
    if content.target_job:
        document.add_paragraph(f"求职意向：{content.target_job}")

    if content.summary:
        heading("个人简介")
        document.add_paragraph(content.summary)
    if content.education:
        heading("教育经历")
        for item in content.education:
            document.add_paragraph(" | ".join(value for value in (
                item.school, item.major, item.degree, item.period,
            ) if value))
    if content.skills:
        heading("专业技能")
        for item in content.skills:
            document.add_paragraph(item.name + (f"：{item.evidence}" if item.evidence else ""))
    for label, entries, name_field in (
        ("项目经历", content.projects, "name"),
        ("实习经历", content.internships, "company"),
    ):
        if not entries:
            continue
        heading(label)
        for item in entries:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.keep_with_next = bool(item.bullets)
            paragraph.add_run(" | ".join(value for value in (
                getattr(item, name_field), item.role, item.period,
            ) if value)).bold = True
            for bullet in item.bullets:
                document.add_paragraph(f"• {bullet}")
    if content.awards:
        heading("获奖情况")
        for award in content.awards:
            document.add_paragraph(award)

    output = BytesIO()
    document.save(output)
    return output.getvalue()
