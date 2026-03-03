def map_env_to_dict(env: list[str] | None) -> dict:
    """
    Maps list of env vars to {key:value} dict
    """
    _env = {}
    if not env:
        return _env
    for e in env:
        if "=" in e:
            k, v = e.split("=", 1)
            _env[k] = v
    return _env
