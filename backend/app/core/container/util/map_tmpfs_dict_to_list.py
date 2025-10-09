from pathlib import Path
from typing import Dict


def map_tmpfs_dict_to_list(
    tmpfs: Dict[Path, str] | None,
) -> list[str]:
    res: list[str] = []
    if not tmpfs:
        return []
    for k, v in tmpfs.items():
        item: str = str(k)
        if v:
            item += f":{v}"
    return [f"{k}:{v}" for k, v in tmpfs.items()]
