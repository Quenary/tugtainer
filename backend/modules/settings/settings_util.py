from backend.modules.settings.settings_enum import ESettingType


def get_setting_typed_value(value: str, value_type: str) -> bool | float | int | str:
    """
    Helper func to get typed app setting value
    """
    try:
        if value_type == ESettingType.BOOL:
            return value.lower() == "true"
        elif value_type == ESettingType.FLOAT:
            return float(value)
        elif value_type == ESettingType.INT:
            return int(value)
        return value
    except Exception:
        return value
