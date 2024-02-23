from django.db import models


class GrowthState(models.TextChoices):
    PENDING = "pending", "Pending"
    GROWING = "growing", "Growing"
    COMPLETE = "complete", "Complete"
    ERROR = "error", "Error"


class GrowthStrategy(models.TextChoices):
    FREEZE = "freeze", "Freeze"
    REVISE = "revise", "Revise"
    RESET = "reset", "Reset"
    STACK = "stack", "Stack"
