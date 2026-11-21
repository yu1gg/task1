from types import SimpleNamespace

from app.services.matching import compute_match
from app.services.skills import normalize_skill


def job_skill(name, importance, required_level):
    return SimpleNamespace(
        name=name,
        importance=importance,
        required_level=required_level,
    )


def test_normalize_skill():
    assert normalize_skill("  Python  ") == "python"
    assert normalize_skill("Machine   Learning") == "machine learning"


def test_score_and_gaps():
    student_skills = [
        {"name": "Python", "level": 4},
        {"name": "SQL", "level": 3},
    ]
    job_skills = [
        job_skill("python", "must", 5),
        job_skill("SQL", "nice", 3),
    ]

    result = compute_match(student_skills, job_skills)

    assert result.score == 85
    assert result.has_job_skills is True
    assert len(result.gaps) == 1
    assert result.gaps[0].name == "python"
    assert result.gaps[0].student_level == 4
    assert result.gaps[0].required_level == 5


def test_no_job_skills():
    result = compute_match([{"name": "Python", "level": 5}], [])
    assert result.score == 0
    assert result.has_job_skills is False
    assert result.gaps == []


def test_student_without_skills_gets_zero():
    result = compute_match([], [job_skill("Python", "must", 3)])
    assert result.score == 0
    assert len(result.gaps) == 1
    assert result.gaps[0].student_level == 0


def test_multiple_entries_take_max_level():
    result = compute_match(
        [
            {"name": "Python", "level": 2},
            {"name": " python ", "level": 4},
        ],
        [job_skill("Python", "must", 4)],
    )
    assert result.score == 100
    assert result.gaps == []


def test_normalize_skill_aliases():
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("Py") == "python"
    assert normalize_skill("torch") == "pytorch"
    assert normalize_skill("大模型") == "large language model"


def test_gap_ordering_must_first_then_largest_deficit():
    result = compute_match(
        [],
        [
            job_skill("A-nice", "nice", 5),
            job_skill("B-must", "must", 2),
            job_skill("C-must", "must", 5),
        ],
    )
    assert [gap.name for gap in result.gaps] == ["C-must", "B-must", "A-nice"]


def test_matched_payload_and_fractional_coverage():
    result = compute_match(
        [{"name": "Python", "level": 5}, {"name": "SQL", "level": 2}],
        [job_skill("Python", "must", 5), job_skill("SQL", "nice", 4)],
    )
    assert result.score == 88
    assert len(result.matched) == 1
    assert result.matched[0]["name"] == "Python"
    assert result.matched[0]["coverage"] == 1.0
    assert len(result.gaps) == 1
    assert result.gaps[0].name == "SQL"


def test_malformed_required_level_defaults_to_three():
    result = compute_match(
        [{"name": "Python", "level": 2}],
        [job_skill("Python", "must", None)],
    )
    assert result.score == 67
    assert result.gaps[0].required_level == 3


def test_ignores_non_dict_student_entries():
    result = compute_match(
        [None, {"name": "Python", "level": 3}],
        [job_skill("Python", "must", 3)],
    )
    assert result.score == 100
