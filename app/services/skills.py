def normalize_skill(name: str) -> str:
    return " ".join(str(name).strip().lower().split())
