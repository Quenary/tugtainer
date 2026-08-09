from typing import Final

# Docker CLI (opts.ValidateLabel) rejects a label before it reaches the daemon
# when its key is empty or contains a space/tab. The daemon itself accepts such
# keys, so containers created through the API/compose may carry labels that
# cannot be passed back through `docker create --label`.
LABEL_KEY_WHITESPACES: Final = " \t"


def filter_cli_safe_labels(
    labels: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Split labels into ones that docker CLI accepts and ones it rejects.
    :returns 0: accepted
    :returns 1: rejected
    """
    accepted: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for key, value in labels.items():
        is_safe = (
            isinstance(key, str)
            and bool(key)
            and not any(ws in key for ws in LABEL_KEY_WHITESPACES)
        )
        if is_safe:
            accepted[key] = value
        else:
            rejected[key] = value
    return accepted, rejected
