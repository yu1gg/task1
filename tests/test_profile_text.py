from app.services.profile_text import (
    format_awards,
    format_blocks,
    format_education,
    format_skills,
    parse_awards,
    parse_blocks,
    parse_education,
    parse_skills,
)


def test_education_roundtrip():
    text = "某某大学 | 人工智能 | 本科 | 2023-2027\n另一所大学 | 计算机 | 硕士 | 2027-2030"
    items = parse_education(text)
    assert items[0]["school"] == "某某大学"
    assert items[1]["degree"] == "硕士"
    assert format_education(items) == text


def test_projects_blocks_roundtrip():
    text = (
        "智能简历系统 | 后端 | 2026.03-2026.05\n"
        "负责 FastAPI 与 LLM 集成\n\n"
        "课程项目 | 成员 | 2025"
    )
    items = parse_blocks(text, ["name", "role", "period"])
    assert items[0]["name"] == "智能简历系统"
    assert "FastAPI" in items[0]["description"]
    assert items[1]["name"] == "课程项目"
    assert format_blocks(items, ["name", "role", "period"]) == text


def test_awards_roundtrip():
    text = "校级奖学金\nACM 校赛二等奖"
    items = parse_awards(text)
    assert len(items) == 2
    assert format_awards(items) == text


def test_skills_parse_clamps_and_formats():
    items = parse_skills("Python | 9 | 课程项目\nSQL | abc")
    assert items[0]["level"] == 5
    assert items[1]["level"] == 3
    assert items[0]["evidence"] == "课程项目"
    assert "Python | 5 | 课程项目" in format_skills(items)


def test_projects_preserve_blank_lines_in_description():
    text = "P | R | T\nline1\n\nline2\n\nQ | R | T"
    items = parse_blocks(text, ["name", "role", "period"])
    assert len(items) == 2
    assert items[0]["description"] == "line1\n\nline2"
    assert items[1]["name"] == "Q"


def test_format_skills_null_level_defaults_to_three():
    assert (
        format_skills([{"name": "Python", "level": None, "evidence": ""}])
        == "Python | 3 | "
    )


def test_short_header_is_padded_not_dropped():
    items = parse_blocks("课程项目 | 成员", ["name", "role", "period"])
    assert len(items) == 1
    assert items[0]["name"] == "课程项目"
    assert items[0]["role"] == "成员"
    assert items[0]["period"] == ""


def test_pipe_heavy_description_without_blank_line_stays_in_description():
    text = "P | R | T\n技术栈 | FastAPI | Vue\n\nQ | R | T"
    items = parse_blocks(text, ["name", "role", "period"])
    assert len(items) == 2
    assert items[0]["description"] == "技术栈 | FastAPI | Vue"
    assert items[1]["name"] == "Q"
