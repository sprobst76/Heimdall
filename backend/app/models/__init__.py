"""SQLAlchemy ORM models.

All models are imported here so that Alembic can discover them
via ``Base.metadata`` when generating migrations.
"""

from app.models.app_group import AppGroup, AppGroupApp  # noqa: F401
from app.models.day_type import DayTypeOverride  # noqa: F401
from app.models.device import Device, DeviceCoupling  # noqa: F401
from app.models.family import Family  # noqa: F401
from app.models.invitation import FamilyInvitation  # noqa: F401
from app.models.quest import QuestInstance, QuestTemplate  # noqa: F401
from app.models.tan import TAN  # noqa: F401
from app.models.time_rule import TimeRule  # noqa: F401
from app.models.usage import UsageEvent  # noqa: F401
from app.models.usage_reward import UsageRewardLog, UsageRewardRule  # noqa: F401
from app.models.user import RefreshToken, User  # noqa: F401

__all__ = [
    "AppGroup",
    "AppGroupApp",
    "DayTypeOverride",
    "Device",
    "DeviceCoupling",
    "Family",
    "FamilyInvitation",
    "QuestInstance",
    "QuestTemplate",
    "RefreshToken",
    "TAN",
    "TimeRule",
    "UsageEvent",
    "UsageRewardLog",
    "UsageRewardRule",
    "User",
]
