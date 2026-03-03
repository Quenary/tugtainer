from pathlib import Path
from typing import Dict


def map_tmpfs_dict_to_list(
    tmpfs: Dict[Path, str] | None,
) -> list[str]:
    """
    Map docker inspect tmpfs dict to list of valid strs.
    """
    res: list[str] = []
    if not tmpfs:
        return []
    for k, v in tmpfs.items():
        # key is path, and value is options
        item: str = str(k)
        if v:
            item += f":{v}"
        res.append(item)
    return res
