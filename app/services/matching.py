from dataclasses import dataclass, field

from app.services.skills import normalize_skill


@dataclass
class MatchGap:
    name: str
    required_level: int
    student_level: int
    importance: str


@dataclass
class MatchResult:
    score: int
    gaps: list[MatchGap] = field(default_factory=list)
    matched: list[dict] = field(default_factory=list)
    has_job_skills: bool = True


def compute_match(student_skills: list[dict], job_skills: list) -> MatchResult:
    normalized: dict[str, int] = {}
    for item in student_skills or []:
        key = normalize_skill(item.get("name", ""))
        if not key:
            continue
        try:
            level = int(item.get("level", 0))
        except (TypeError, ValueError):
            level = 0
        level = max(0, min(5, level))
        normalized[key] = max(normalized.get(key, 0), level)

    if not job_skills:
        return MatchResult(score=0, has_job_skills=False)

    total_weight = 0
    weighted_score = 0.0
    gaps: list[MatchGap] = []
    matched: list[dict] = []

    for skill in job_skills:
        required_level = max(1, min(5, int(skill.required_level)))
        weight = 3 if skill.importance == "must" else 1
        student_level = normalized.get(normalize_skill(skill.name), 0)
        coverage = min(student_level / required_level, 1.0)

        total_weight += weight
        weighted_score += weight * coverage

        entry = {
            "name": skill.name,
            "importance": skill.importance,
            "required_level": required_level,
            "student_level": student_level,
            "coverage": round(coverage, 2),
        }
        if coverage >= 1:
            matched.append(entry)
        else:
            gaps.append(
                MatchGap(
                    name=skill.name,
                    required_level=required_level,
                    student_level=student_level,
                    importance=skill.importance,
                )
            )

    score = round(100 * weighted_score / total_weight) if total_weight else 0
    gaps.sort(
        key=lambda gap: (
            0 if gap.importance == "must" else 1,
            -(gap.required_level - gap.student_level),
        )
    )
    return MatchResult(
        score=score,
        gaps=gaps,
        matched=matched,
        has_job_skills=True,
    )
