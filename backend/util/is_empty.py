def is_empty(v):
    """
    Checks if a value is considered empty.
    - None
    - Empty containers (list, dict, tuple, set)
    - Empty strings or strings with only spaces
    """
    if v is None:
        return True
    if isinstance(v, (list, dict, tuple, set)) and len(v) == 0:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False
