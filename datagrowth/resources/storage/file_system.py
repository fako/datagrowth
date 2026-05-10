from typing import Any, cast
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError
from pydantic import BaseModel

from datagrowth.configuration import ConfigurationProperty, ConfigurationType
from datagrowth.exceptions import DGTemplateNotFound, DGTemplateRenderError
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.signatures import Signature
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.resources.pydantic import Resource


class FileSystemStorage:

    tag = Tag(category="storage", value="file_system")
    config = ConfigurationProperty(namespace="storage")

    def __init__(self, config: ConfigurationType, jinja_environment: Environment | None = None) -> None:
        self.config = config
        self.jinja_environment = jinja_environment or Environment()

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

    def _get_storage_directory(self, signature: Signature, is_tmp: bool = False) -> Path:
        if is_tmp:
            base_dir = self._resolve_directory("tmp")
        elif self.config.snapshots:
            base_dir = self._resolve_directory("snapshots")
        else:
            base_dir = self._resolve_directory("data")
        if signature.type:
            base_dir = base_dir / signature.type
        return base_dir / str(signature.hash)

    def save(self, resource: ResourceProtocol) -> Signature:
        if not self.config.allow_save:
            raise PermissionError("Saving resources is disabled by storage config (allow_save=false).")
        if resource.signature is None:
            raise ValueError("Can't save resource without a signature.")

        directory = self._get_storage_directory(resource.signature)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "data.json"
        assert isinstance(resource, BaseModel), "FileSystemStorage only supports Pydantic-based resources."
        path.write_text(resource.model_dump_json(indent=4), encoding="utf-8")
        return resource.signature

    def load(self, signature: Signature, load_as: type[ResourceProtocol] | None = None) -> ResourceProtocol | None:
        if not self.config.allow_load:
            raise PermissionError("Loading resources is disabled by storage config (allow_load=false).")

        path = self._get_storage_directory(signature) / "data.json"
        if not path.exists():
            return None
        load_cls = load_as or Resource[Signature]
        assert issubclass(load_cls, BaseModel), "FileSystemStorage only supports Pydantic-based resources."
        loaded = load_cls.model_validate_json(path.read_text(encoding="utf-8"))
        return cast(ResourceProtocol, loaded)

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

    def read_tmp(self, filename: str) -> bytes | str:
        if not self.config.allow_read:
            raise PermissionError("Reading files is disabled by storage config (allow_read=false).")

        filename_path = Path(filename)
        if filename_path.is_absolute():
            raise ValueError("Filename must be a relative path in the tmp directory.")
        if filename_path.name != str(filename_path):
            raise ValueError("Nested paths are not allowed in the tmp directory.")
        if filename_path.name == "data.json":
            raise ValueError("Filename 'data.json' is reserved for storage.save() and storage.load().")

        path = self._resolve_directory("tmp") / filename_path.name
        data = path.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data

    def write_tmp(self, filename: str, data: bytes | str) -> Path:
        if not self.config.allow_write:
            raise PermissionError("Writing files is disabled by storage config (allow_write=false).")

        filename_path = Path(filename)
        if filename_path.is_absolute():
            raise ValueError("Filename must be a relative path in the tmp directory.")
        if filename_path.name != str(filename_path):
            raise ValueError("Nested paths are not allowed in the tmp directory.")
        if filename_path.name == "data.json":
            raise ValueError("Filename 'data.json' is reserved for storage.save() and storage.load().")

        path = self._resolve_directory("tmp") / filename_path.name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_bytes(data)
        return path

    def render_template(self, template: str, context: dict[str, Any]) -> str:
        directories: list[str] = []

        for tag in DATAGROWTH_REGISTRY.tags_by_category("templates"):
            directory = DATAGROWTH_REGISTRY.directories.get(tag)
            if directory is None:
                continue
            resolved_directory = directory if directory.is_absolute() else (Path.cwd() / directory)
            directory_path = str(resolved_directory)
            if directory_path not in directories:
                directories.append(directory_path)

        templates_directory = self._resolve_directory("templates")
        resolved_templates_directory = (
            templates_directory if templates_directory.is_absolute() else (Path.cwd() / templates_directory)
        )
        templates_path = str(resolved_templates_directory)
        if templates_path not in directories:
            directories.append(templates_path)

        loader = FileSystemLoader(directories)
        environment = self.jinja_environment.overlay(loader=loader)
        try:
            return environment.get_template(template).render(context)
        except TemplateNotFound as error:
            raise DGTemplateNotFound(
                f"Template '{template}' was not found in configured template directories.",
                template
            ) from error
        except TemplateError as error:
            raise DGTemplateRenderError(
                f"Error rendering template '{template}': {error}",
                template
            ) from error


DATAGROWTH_REGISTRY.register_storage(FileSystemStorage.tag, FileSystemStorage)
