from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

from app.schemas import ResumeContent
from app.services.resume_docx import export_resume_docx


def test_exports_all_sections_and_preserves_special_characters():
    content = ResumeContent(
        name="张三", phone="13800000000", email="student@example.com",
        target_job="Python 开发", summary="认真负责。",
        education=[dict(school="示例大学", major="计算机", degree="本科", period="2022–2026")],
        skills=[dict(name="Python", evidence="项目使用 A&B <模块>")],
        projects=[dict(name="招聘平台", role="开发", period="2025", bullets=["实现登录功能。"])],
        internships=[dict(company="示例公司", role="实习生", period="2025", bullets=["维护测试用例。"])],
        awards=["校级奖学金"],
    )
    result = export_resume_docx(content)
    assert isinstance(result, bytes)
    document = Document(BytesIO(result))
    paragraphs = [p.text for p in document.paragraphs]
    text = "\n".join(paragraphs)
    for value in ("张三", "13800000000", "student@example.com", "Python 开发", "示例大学", "A&B <模块>", "实现登录功能。", "维护测试用例。", "校级奖学金"):
        assert value in text
    headings = [p for p in paragraphs if p in ("个人简介", "教育经历", "专业技能", "项目经历", "实习经历", "获奖情况")]
    assert headings == ["个人简介", "教育经历", "专业技能", "项目经历", "实习经历", "获奖情况"]
    assert not document.tables


def test_exports_a4_chinese_font_and_hides_empty_sections():
    document = Document(BytesIO(export_resume_docx(ResumeContent(name="李四", target_job="测试"))))
    section = document.sections[0]
    # DOCX stores page dimensions in integer twips (1/20 pt).
    assert abs(section.page_width - Mm(210)) < Mm(0.02)
    assert abs(section.page_height - Mm(297)) < Mm(0.02)
    for margin in (section.top_margin, section.bottom_margin, section.left_margin, section.right_margin):
        assert abs(margin - Mm(15)) < Mm(0.02)
    normal = document.styles["Normal"]
    assert normal.font.size == Pt(10.5)
    assert normal.element.rPr.rFonts.get(qn("w:eastAsia")) == "宋体"
    assert normal.paragraph_format.keep_together
    assert "教育经历" not in [p.text for p in document.paragraphs]
    assert "实习经历" not in [p.text for p in document.paragraphs]
