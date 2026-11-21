ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "py": "python",
    "python3": "python",
    "mysql": "sql",
    "postgresql": "sql",
    "torch": "pytorch",
    "pytorch": "pytorch",
    "tf": "tensorflow",
    "tensorflow": "tensorflow",
    "ml": "machine learning",
    "machine learning": "machine learning",
    "深度学习": "deep learning",
    "deep learning": "deep learning",
    "llm": "large language model",
    "大模型": "large language model",
    "large language model": "large language model",
}


def normalize_skill(name: str) -> str:
    key = " ".join(str(name).strip().lower().split())
    return ALIASES.get(key, key)
