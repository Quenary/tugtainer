from backend.app.enums.settings_enum import ESettingType


def get_setting_typed_value(value: str, value_type: str):
    """
    Helper func to get typed app setting value
    """
    res = value
    try:
        if value_type == ESettingType.BOOL:
            res = res.lower() == "true"
        elif value_type == ESettingType.FLOAT:
            res = float(res)
        elif value_type == ESettingType.INT:
            res = int(res)
    except Exception:
        pass
    return res
