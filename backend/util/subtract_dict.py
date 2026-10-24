from typing import Any


def subtract_dict(
    d1: dict[Any, Any] | None, d2: dict[Any, Any] | None
) -> dict[Any, Any] | None:
    """
    Return dict with unique keys from d1.
    :param d1: dict
    :param d2: dict
    :return: dict
    """
    if not d1:
        return None
    if not d2:
        return d1
    return {k: v for k, v in d1.items() if k not in d2}


def subtract_dict_items(
    d1: dict[Any, Any] | None, d2: dict[Any, Any] | None
) -> dict[Any, Any]:
    """
    Return items from d1 that are not present in d2
    with the same value (unlike subtract_dict, which compares keys only).
    :param d1: dict
    :param d2: dict
    :return: dict
    """
    if not d1:
        return {}
    if not d2:
        return dict(d1)
    return {k: v for k, v in d1.items() if k not in d2 or d2[k] != v}
