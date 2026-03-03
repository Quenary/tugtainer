import re

DOCKER_LABEL_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def filter_valid_docker_labels(
    labels: dict,
) -> tuple[dict, dict]:
    """
    Filter labels by keys that matches docker requirements.
    :returns 0: valid
    :returns 1: invalid
    """
    valid = {}
    invalid = {}
    for k, v in labels.items():
        if isinstance(k, str) and DOCKER_LABEL_KEY_RE.match(k):
            valid[k] = v
        else:
            invalid[k] = v
    return valid, invalid
