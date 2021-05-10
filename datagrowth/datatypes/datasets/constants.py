from enum import Enum


class GrowthState(Enum):
    PENDING = "Pending"
    SEEDING = "Seeding"
    GROWING = "Growing"
    COMPLETE = "Complete"
