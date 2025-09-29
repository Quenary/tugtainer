
def subtract_dict(d1: dict, d2: dict) -> dict:
    """
    Return dict with unique keys from d1.
    :param d1: dict
    :param d2: dict
    :return: dict
    """
    return {k: v for k, v in d1.items() if k not in d2}