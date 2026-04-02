from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


class Tag(BaseModel):
    category: str
    value: str

    @classmethod
    def from_strings(cls, *args: str) -> list[Tag]:
        return [cls.from_string(string) for string in args]

    @classmethod
    def from_string(cls, string: str) -> Tag:
        assert string.count(":") == 1, \
            "Expected Tag string to contain a single semicolon separating categories and values"
        category, value = string.split(":")
        return cls(category=category, value=value)

    def __str__(self) -> str:
        return f"{self.category}:{self.value}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class TagRegistry:
    tags: dict[str, Tag]

    @classmethod
    def from_tags(cls, tags: list[Tag]) -> TagRegistry:
        return TagRegistry(
            tags={str(tag): tag for tag in tags}
        )

    def register(self, tag: str | Tag) -> Tag:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        self.tags[str(tag)] = tag
        return tag

    def unregister(self, tag: str | Tag) -> None:
        if isinstance(tag, Tag):
            tag = str(tag)
        del self.tags[tag]

    def tags_by_category(self, category: str) -> list[Tag]:
        return [tag for tag in self.tags.values() if tag.category == category]

    def tags_by_value(self, value: str) -> list[Tag]:
        return [tag for tag in self.tags.values() if tag.value == value]
