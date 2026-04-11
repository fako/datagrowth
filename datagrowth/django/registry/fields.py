from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import fields

from datagrowth.registry import Tag


class TagField(fields.CharField):
    """
    Store a datagrowth Tag as "category:value" in a varchar column.
    """

    description = "A datagrowth Tag represented as category:value"

    def __init__(self, *args: Any, category: str | None = None, categories: Iterable[str] | None = None,
                 **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 255)
        if category is not None and categories is not None:
            raise ValueError("TagField accepts either 'category' or 'categories', not both.")
        if category is not None:
            self._categories = (category.lower(),)
        elif categories is not None:
            self._categories = tuple(tag_category.lower() for tag_category in categories)
        else:
            self._categories = None
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        if self._categories is not None:
            kwargs["categories"] = self._categories
        return name, path, args, kwargs

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> Tag | None:
        if value is None:
            return None
        return self.to_python(value)

    def to_python(self, value: Any) -> Tag | None:
        if value is None:
            return None
        if isinstance(value, Tag):
            self._validate_category(value)
            return value
        if isinstance(value, str):
            try:
                tag = Tag.from_string(value)
                self._validate_category(tag)
                return tag
            except AssertionError as error:
                raise ValidationError(f"Enter a valid tag in the form 'category:value': {value}") from error
        raise ValidationError(f"Expected a Tag or string value, but received {type(value).__name__}.")

    def get_prep_value(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(self.to_python(value))

    def _validate_category(self, tag: Tag) -> None:
        if self._categories is None:
            return
        category = tag.category.lower()
        if category not in self._categories:
            allowed = ", ".join(self._categories)
            raise ValidationError(f"Tag category '{tag.category}' is not allowed. Expected one of: {allowed}.")
