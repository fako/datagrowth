from typing import ClassVar

from datagrowth.registry import Tag
from datagrowth.vendors.openai.resources import (
    OpenaiPromptResource as OpenaiPromptResourceNoStorage, PromptInputsValidator, OPENAI_DEFAULT_TAG, OPENAI_DEFAULT_MODEL  # noqa: E501
)

__all__ = [
    "OpenaiPromptResource",
    "PromptInputsValidator",
    "OPENAI_DEFAULT_TAG",
    "OPENAI_DEFAULT_MODEL",
]


class OpenaiPromptResource(OpenaiPromptResourceNoStorage):
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")
