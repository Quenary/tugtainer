from pathlib import Path


def normalize_path(value: Path | str | None) -> str | None:
    """Normalize path before passing it as argument to python_on_whales"""
    if not value:
        return None
    if isinstance(value, Path):
        s = str(value)
        return None if s == "." else s
    return value
