from __future__ import annotations

from typing import Any
import importlib
from pydantic import BaseModel


def serialize_class_reference(value: Any, prefix: str | None = None) -> Any:
    if isinstance(value, dict):
        return {key: serialize_class_reference(inner, prefix=prefix) for key, inner in value.items()}
    if isinstance(value, list):
        return [serialize_class_reference(inner, prefix=prefix) for inner in value]
    if isinstance(value, tuple):
        return tuple(serialize_class_reference(inner, prefix=prefix) for inner in value)
    if not isinstance(value, type):
        return value

    path = f"{value.__module__}.{value.__qualname__}"
    if prefix == "basemodel" and issubclass(value, BaseModel):
        return f"{prefix}:{path}"
    return path


def deserialize_class_reference(value: Any, prefix: str | None = None) -> Any:
    if isinstance(value, dict):
        return {key: deserialize_class_reference(inner, prefix=prefix) for key, inner in value.items()}
    if isinstance(value, list):
        return [deserialize_class_reference(inner, prefix=prefix) for inner in value]
    if isinstance(value, tuple):
        return tuple(deserialize_class_reference(inner, prefix=prefix) for inner in value)
    if not isinstance(value, str):
        return value

    class_path = value
    if prefix:
        prefix_token = f"{prefix}:"
        if not value.startswith(prefix_token):
            return value
        class_path = value.removeprefix(prefix_token)

    parts = class_path.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        attr_path = parts[index:]
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name == module_name:
                continue
            raise
        clazz: Any = module
        for attribute in attr_path:
            clazz = getattr(clazz, attribute)
        if not isinstance(clazz, type):
            raise TypeError(f"Expected class import from path '{class_path}', got {type(clazz)}")
        return clazz
    raise ImportError(f"Could not import class path '{class_path}'")
