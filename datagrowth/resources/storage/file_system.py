import os
from uuid import uuid4
from typing import Any
from pathlib import Path

from datagrowth.configuration import ConfigurationProperty, ConfigurationType
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.signatures import Signature
from datagrowth.resources.pydantic import Resource


class FileSystemStorage:

    tag = Tag(category="storage", value="file_system")
    config = ConfigurationProperty(namespace="storage")

    def __init__(self, config: ConfigurationType | dict[str, Any]) -> None:
        self.config = config
        if getattr(self.config, "snapshots", False):
            # Snapshots are an explicit persistence mode.
            self.config.force_save = True
        assert not (self.config.force_save and not self.config.allow_save), "Can't force_save when saves are not allowed."  # noqa: E501
        assert not (self.config.force_load and not self.config.allow_load), "Can't force_load when loads are not allowed."  # noqa: E501
        assert not self.config.force_save or not self.config.force_load, "Can't force_save and force_load at the same time."  # noqa: E501

    def _resolve_directory(self, key: str) -> Path:
        raw_directories = self.config.get("directories", {})
        if not isinstance(raw_directories, dict):
            raise TypeError("Storage directories configuration should be a dictionary.")
        value = raw_directories.get(key)
        if value is None:
            return Path.cwd()

        if isinstance(value, Path):
            directory = value
        elif isinstance(value, str):
            directory = Path(value)
        elif isinstance(value, (list, tuple)):
            if not value:
                return Path.cwd()
            parts = [str(part) for part in value]
            if parts[0] == "/":
                if os.name == "nt":
                    # Single config definition for absolute paths:
                    # "/" maps to the active drive root on Windows (e.g. C:\).
                    anchor = Path.cwd().anchor or "\\"
                    directory = Path(anchor, *parts[1:])
                else:
                    directory = Path("/", *parts[1:])
            else:
                directory = Path(*parts)
        else:
            raise TypeError(f"Unsupported directory configuration type for '{key}': {type(value)}")

        return directory if directory.is_absolute() else (Path.cwd() / directory)

    def _get_storage_directory(self) -> Path:
        if self.config.snapshots:
            return self._resolve_directory("snapshots")
        return self._resolve_directory("data")

    def save(self, resource: Resource[Signature]) -> Signature:
        if not self.config.allow_save:
            raise PermissionError("Saving resources is disabled by storage config (allow_save=false).")
        if resource.signature is None:
            raise ValueError("Can't save resource without a signature.")

        directory = self._resolve_directory("data")
        if self.config.snapshots:
            directory = self._resolve_directory("snapshots")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{resource.signature.hash}.json"
        path.write_text(resource.model_dump_json(indent=4), encoding="utf-8")
        return resource.signature

    def load(self, signature: Signature) -> Resource[Signature] | None:
        if not self.config.allow_load:
            raise PermissionError("Loading resources is disabled by storage config (allow_load=false).")

        directory = self._resolve_directory("data")
        if self.config.snapshots:
            directory = self._resolve_directory("snapshots")
        path = directory / f"{signature.hash}.json"
        if not path.exists():
            return None
        return Resource[Signature].model_validate_json(path.read_text(encoding="utf-8"))

    def read(self, path: Path) -> bytes | str:
        if not self.config.allow_read:
            raise PermissionError("Reading files is disabled by storage config (allow_read=false).")

        tmp_directory = self._resolve_directory("tmp")
        target = path if path.is_absolute() else tmp_directory / path
        data = target.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data

    def write(self, data: bytes | str) -> Path:
        if not self.config.allow_write:
            raise PermissionError("Writing files is disabled by storage config (allow_write=false).")

        tmp_directory = self._resolve_directory("tmp")
        tmp_directory.mkdir(parents=True, exist_ok=True)
        extension = ".txt" if isinstance(data, str) else ".bin"
        path = tmp_directory / f"{uuid4().hex}{extension}"
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        return path


DATAGROWTH_REGISTRY.register_storage(FileSystemStorage.tag, FileSystemStorage)
