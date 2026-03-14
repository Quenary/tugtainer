import random


def jitter(value: int | float, jitter: int = 15) -> float:
    """
    Apply jitter to value, random from -jitter to +jitter percentage.

    Example:
        jitter(5, 15) -> random value between 4.25 and 5.75
    """
    factor = 1 + random.uniform(-jitter, jitter) / 100
    return value * factor
