from .is_empty import is_empty


def drop_empty_keys(cfg: dict) -> dict:
    """
    Drops 'empty' values from dict:
    - None
    - Empty containers (list, dict, tuple, set)
    - Empty strings or strings with only spaces
    """

    return {k: v for k, v in cfg.items() if not is_empty(v)}
