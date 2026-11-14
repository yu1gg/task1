def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def parse_education(text: str) -> list[dict]:
    items = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split("|")]
        parts += [""] * (4 - len(parts))
        items.append(
            {
                "school": parts[0],
                "major": parts[1],
                "degree": parts[2],
                "period": parts[3],
            }
        )
    return items


def format_education(items: list[dict]) -> str:
    return "\n".join(
        " | ".join(
            [
                item.get("school", ""),
                item.get("major", ""),
                item.get("degree", ""),
                item.get("period", ""),
            ]
        )
        for item in items or []
    )


def parse_blocks(text: str, fields: list[str]) -> list[dict]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in (text or "").splitlines():
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line.strip())

    if current:
        blocks.append(current)

    items = []
    for block in blocks:
        header = [part.strip() for part in block[0].split("|")]
        header += [""] * (len(fields) - len(header))
        item = {field: header[index] for index, field in enumerate(fields)}
        item["description"] = "\n".join(block[1:]).strip()
        items.append(item)
    return items


def format_blocks(items: list[dict], fields: list[str]) -> str:
    blocks = []
    for item in items or []:
        header = " | ".join(item.get(field, "") for field in fields)
        description = item.get("description", "")
        blocks.append(header + ("\n" + description if description else ""))
    return "\n\n".join(blocks)


def parse_awards(text: str) -> list[dict]:
    return [{"name": line} for line in _split_lines(text)]


def format_awards(items: list[dict]) -> str:
    return "\n".join(item.get("name", "") for item in items or [])


def parse_skills(text: str) -> list[dict]:
    skills = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split("|")]
        name = parts[0] if parts else ""
        if not name:
            continue

        level = 3
        if len(parts) > 1:
            try:
                level = int(parts[1])
            except ValueError:
                level = 3
        level = max(1, min(5, level))

        evidence = parts[2] if len(parts) > 2 else ""
        skills.append({"name": name, "level": level, "evidence": evidence})
    return skills


def format_skills(items: list[dict]) -> str:
    return "\n".join(
        f"{item.get('name', '')} | {item.get('level', 3)} | {item.get('evidence', '')}"
        for item in items or []
    )
