import os
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

    def _get_storage_directory(self, signature: Signature) -> Path:
        base_dir = self._resolve_directory("data")
        if self.config.snapshots:
            base_dir = self._resolve_directory("snapshots")
        if signature.type:
            base_dir = base_dir / signature.type
        return base_dir / str(signature.hash)

    def save(self, resource: Resource[Signature]) -> Signature:
        if not self.config.allow_save:
            raise PermissionError("Saving resources is disabled by storage config (allow_save=false).")
        if resource.signature is None:
            raise ValueError("Can't save resource without a signature.")

        directory = self._get_storage_directory(resource.signature)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "data.json"
        path.write_text(resource.model_dump_json(indent=4), encoding="utf-8")
        return resource.signature

    def load(self, signature: Signature) -> Resource[Signature] | None:
        if not self.config.allow_load:
            raise PermissionError("Loading resources is disabled by storage config (allow_load=false).")

        path = self._get_storage_directory(signature) / "data.json"
        if not path.exists():
            return None
        return Resource[Signature].model_validate_json(path.read_text(encoding="utf-8"))

    def read(self, signature: Signature, filename: str) -> bytes | str:
        if not self.config.allow_read:
            raise PermissionError("Reading files is disabled by storage config (allow_read=false).")

        filename_path = Path(filename)
        if filename_path.is_absolute():
            raise ValueError("Filename must be a relative path in the signature directory.")
        if filename_path.name != str(filename_path):
            raise ValueError("Nested paths are not allowed in the signature directory.")
        if filename_path.name == "data.json":
            raise ValueError("Filename 'data.json' is reserved for storage.save() and storage.load().")

        target = self._get_storage_directory(signature) / filename_path.name
        data = target.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data

    def write(self, signature: Signature, filename: str, data: bytes | str) -> Path:
        if not self.config.allow_write:
            raise PermissionError("Writing files is disabled by storage config (allow_write=false).")

        filename_path = Path(filename)
        if filename_path.is_absolute():
            raise ValueError("Filename must be a relative path in the signature directory.")
        if filename_path.name != str(filename_path):
            raise ValueError("Nested paths are not allowed in the signature directory.")
        if filename_path.name == "data.json":
            raise ValueError("Filename 'data.json' is reserved for storage.save() and storage.load().")

        path = self._get_storage_directory(signature) / filename_path.name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        return path


DATAGROWTH_REGISTRY.register_storage(FileSystemStorage.tag, FileSystemStorage)
