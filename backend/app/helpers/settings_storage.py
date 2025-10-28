from typing import Any, Literal, overload
from sqlalchemy import event, select
from backend.app.enums import ESettingKey
from backend.app.db.session import async_session_maker
from backend.app.db.models import SettingModel
from backend.app.db.util import get_setting_typed_value


class SettingsStorage:
    """
    Class which stores the current settings values ​​from the database.
    """

    _INSTANCE = None
    _VALUES: dict[ESettingKey, Any] = {}

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    @classmethod
    @overload
    def get(cls, key: Literal[ESettingKey.CRONTAB_EXPR]) -> str: ...
    @classmethod
    @overload
    def get(
        cls, key: Literal[ESettingKey.NOTIFICATION_URL]
    ) -> str: ...
    @classmethod
    @overload
    def get(cls, key: Literal[ESettingKey.TIMEZONE]) -> str: ...
    @classmethod
    @overload
    def get(cls, key: Literal[ESettingKey.DOCKER_TIMEOUT]) -> int: ...
    @classmethod
    def get(cls, key: ESettingKey, default=None):
        """Get value of setting"""
        return cls._VALUES.get(key, default)

    @classmethod
    def all(cls) -> dict[ESettingKey, Any]:
        """Get all values"""
        return dict(cls._VALUES)

    @classmethod
    async def load_one(cls, key: ESettingKey):
        """Load setting by key from db"""
        async with async_session_maker() as session:
            result = await session.execute(
                select(SettingModel).where(
                    SettingModel.key == key.value
                )
            )
            setting = result.scalar_one_or_none()
            if setting:
                cls._VALUES[key] = get_setting_typed_value(
                    setting.value, setting.value_type
                )

    @classmethod
    async def load_all(cls):
        """Load all settings from db"""
        async with async_session_maker() as session:
            result = await session.execute(select(SettingModel))
            rows = result.scalars().all()

        for row in rows:
            try:
                key = ESettingKey(row.key)
            except ValueError:
                continue
            cls._VALUES[key] = get_setting_typed_value(
                row.value, row.value_type
            )


@event.listens_for(SettingModel, "after_update")
def update_setting_value(mapper, connection, target: SettingModel):
    """Update values by db event"""
    try:
        key = ESettingKey(target.key)
    except ValueError:
        return

    SettingsStorage._VALUES[key] = get_setting_typed_value(
        target.value, target.value_type
    )
