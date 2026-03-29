import json
import logging
import os
from importlib import resources
from pathlib import Path
from typing import Any, Literal, Mapping

from invoke.config import Config as InvokeConfig
from invoke.config import merge_dicts

from datagrowth.version import VERSION


LOGGER = logging.getLogger("datagrowth")
ENV_PREFIX = "DATAGROWTH"
AUTODISCOVER = "AUTODISCOVER"
PLAIN_COMPATIBILITY_KEYS = {
    "DATAGROWTH_API_VERSION": "web_api_version",
    "DATAGROWTH_DATETIME_FORMAT": "global_datetime_format",
    "DATAGROWTH_DATA_DIR": "global_data_dir",
    "DATAGROWTH_MEDIA_ROOT": "web_media_root",
    "DATAGROWTH_BIN_DIR": "shell_resource_bin_dir",
    "DATAGROWTH_REQUESTS_PROXIES": "http_resource_requests_proxies",
    "DATAGROWTH_REQUESTS_VERIFY": "http_resource_requests_verify",
    "DATAGROWTH_MAX_BATCH_SIZE": "global_max_batch_size",
}


class DatagrowthInvokeConfig(InvokeConfig):

    prefix = "datagrowth"
    file_prefix = "datagrowth"
    env_prefix = ENV_PREFIX


class InvalidConfigurationError(ValueError):
    pass


def _warn_unknown(source: str, input_key: str, normalized_key: str | None = None) -> None:
    LOGGER.warning(
        "Ignoring unknown datagrowth configuration from %s: input key '%s'%s. "
        "The key is not present in package defaults.",
        source,
        input_key,
        " (normalized to '{}')".format(normalized_key) if normalized_key else ""
    )


def _coerce_env_value(value: str, default_value: Any) -> Any:
    if isinstance(default_value, bool):
        return value.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default_value, int) and not isinstance(default_value, bool):
        try:
            return int(value)
        except ValueError:
            return value
    if isinstance(default_value, float):
        try:
            return float(value)
        except ValueError:
            return value
    if isinstance(default_value, (dict, list)) or default_value is None:
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _discover_project_location(file_prefix: str, suffixes: tuple[str, ...],
                               start_directory: Path | None = None) -> Path | None:
    directory = (start_directory or Path.cwd()).resolve()
    for candidate_directory in (directory, *directory.parents):
        for suffix in suffixes:
            candidate = candidate_directory / "{}.{}".format(file_prefix, suffix)
            if candidate.is_file():
                return candidate_directory
    return None


def _flatten_package_defaults(defaults: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for namespace, values in defaults.items():
        if not isinstance(values, Mapping):
            _warn_unknown("package defaults", str(namespace))
            continue
        for key, value in values.items():
            flattened["{}_{}".format(str(namespace).lower(), str(key).lower())] = value
    return flattened


def _infer_project_allowed_keys(project_config: Mapping[str, Any]) -> set[str]:
    inferred: set[str] = set()

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if hasattr(node, "items") and callable(getattr(node, "items")):
            for key, value in node.items():
                walk(value, path + (str(key).lower(),))
            return
        if not path:
            return
        if len(path) == 1:
            inferred.add("global_{}".format(path[0]))
            return
        inferred.add("_".join(path[:2]))

    walk(project_config, tuple())
    return inferred


def _normalize_namespaced(config: Mapping[str, Any], allowed_keys: set[str], source: str) -> dict[str, Any]:
    """
    Normalize nested configuration to the namespaced flat keys datagrowth uses.

    For each nested path we first try to match an explicit key in ``allowed_keys``.
    If that fails, we try the same key with an implicit ``global_`` prefix.
    Unknown paths are ignored and logged as warnings.

    Examples:
        shell_resource.bin_dir -> shell_resource_bin_dir
        asynchronous -> global_asynchronous (if allowed)

    Nested keys below a matched namespace key remain nested as dict values.
    """
    normalized: dict[str, Any] = {}

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if hasattr(node, "items") and callable(getattr(node, "items")):
            for key, value in node.items():
                walk(value, path + (str(key).lower(),))
            return
        if not path:
            return

        selected_key: str | None = None
        remainder: tuple[str, ...] = tuple()
        for index in range(len(path), 0, -1):
            candidate = "_".join(path[:index])
            if candidate in allowed_keys:
                selected_key = candidate
                remainder = path[index:]
                break
            implicit_global = "global_{}".format(candidate)
            if implicit_global in allowed_keys:
                selected_key = implicit_global
                remainder = path[index:]
                break
        if selected_key is None:
            _warn_unknown(source, "_".join(path).upper())
            return

        value = node
        if not remainder:
            normalized[selected_key] = value
            return
        nested = value
        for segment in reversed(remainder):
            nested = {segment: nested}
        if isinstance(normalized.get(selected_key), dict) and isinstance(nested, dict):
            merge_dicts(normalized[selected_key], nested)  # type: ignore[index]
        else:
            normalized[selected_key] = nested

    walk(config, tuple())
    return normalized


def create_invoke_configuration(project_location: Path | Literal["AUTODISCOVER"] | None = AUTODISCOVER,
                                package_defaults: Mapping[str, Any] | None = None
                                ) -> tuple[DatagrowthInvokeConfig, Mapping[str, Any]]:
    """
    Build a fully loaded invoke configuration object for datagrowth.
    """
    invoke_file_prefix = DatagrowthInvokeConfig.file_prefix or DatagrowthInvokeConfig.prefix
    if invoke_file_prefix is None:
        raise InvalidConfigurationError("DatagrowthInvokeConfig should define a file_prefix or prefix.")

    # Optional project root used by Invoke for per-project config discovery.
    # - AUTODISCOVER: discover a project root by walking up from cwd.
    # - Path: use this explicit project root.
    # - None: explicitly skip project-level overrides (used by tests).
    if project_location == AUTODISCOVER:
        resolved_project_location = _discover_project_location(
            file_prefix=invoke_file_prefix,
            suffixes=("yaml", "yml", "json", "py"),
        )
    elif project_location is None or isinstance(project_location, Path):
        resolved_project_location = project_location
    else:
        raise TypeError("project_location should be pathlib.Path, 'AUTODISCOVER', or None.")
    project_location = str(resolved_project_location) if resolved_project_location is not None else None
    # Case 1: no explicit defaults were injected, so load package defaults through Invoke runtime first.
    if package_defaults is None:
        runtime_filename = "{}.yml".format(invoke_file_prefix)
        runtime_resource = resources.files("datagrowth").joinpath(runtime_filename)
        with resources.as_file(runtime_resource) as runtime_path:
            config = DatagrowthInvokeConfig(
                lazy=True,
                runtime_path=str(runtime_path),
                project_location=project_location,
            )
            config.load_runtime(merge=False)
            package_defaults = getattr(config, "_runtime", {})
            config.load_defaults(dict(package_defaults), merge=False)
            config._set(_runtime={})
    # Case 2: defaults were injected (for example in tests), so use those directly as invoke defaults.
    else:
        config = DatagrowthInvokeConfig(
            defaults=dict(package_defaults),
            lazy=True,
            project_location=project_location,
        )
    if resolved_project_location is not None:
        config.load_project(merge=True)
    config.load_shell_env()
    return config, package_defaults


def _get_django_settings(django_settings: Any | None = None) -> Any | None:
    if django_settings is not None:
        return django_settings
    try:
        from django.conf import settings as project_settings
    except Exception:
        return None
    if not getattr(project_settings, "configured", False):
        return None
    return project_settings


def _django_override_layers(allowed_keys: set[str],
                            django_settings: Any | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if django_settings is None:
        return {}, {}
    if hasattr(django_settings, "DATAGROWTH_DEFAULT_CONFIGURATION"):
        raise InvalidConfigurationError(
            "DATAGROWTH_DEFAULT_CONFIGURATION is no longer supported in Django settings. "
            "Use namespaced DATAGROWTH_* settings instead or specify a datagrowth.yml in your PATH."
        )

    namespaced: dict[str, Any] = {}
    plain: dict[str, Any] = {}

    for key in dir(django_settings):
        if not key.startswith("{}_".format(ENV_PREFIX)):
            continue
        if key in PLAIN_COMPATIBILITY_KEYS:
            continue
        value = getattr(django_settings, key)
        candidate = key[len("{}_".format(ENV_PREFIX)):].lower()
        normalized = candidate if candidate in allowed_keys else "global_{}".format(candidate)
        if normalized not in allowed_keys:
            _warn_unknown("django settings", key, normalized_key=normalized)
            continue
        namespaced[normalized] = value

    for key, normalized in PLAIN_COMPATIBILITY_KEYS.items():
        if not hasattr(django_settings, key):
            continue
        if normalized not in allowed_keys:
            _warn_unknown("django plain compatibility", key, normalized_key=normalized)
            continue
        plain[normalized] = getattr(django_settings, key)

    return namespaced, plain


def _validate_allowed(layer: dict[str, Any], allowed_keys: set[str], source: str) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    for key, value in layer.items():
        if key not in allowed_keys:
            _warn_unknown(source, key.upper(), normalized_key=key)
            continue
        validated[key] = value
    return validated


def _apply_runtime_fallbacks(configuration: dict[str, Any], django_settings: Any | None) -> None:
    if configuration.get("http_resource_user_agent") is None:
        configuration["http_resource_user_agent"] = "DataGrowth (v{})".format(VERSION)

    if django_settings is None:
        return

    base_dir = getattr(django_settings, "BASE_DIR", None)
    if configuration.get("global_data_dir") is None and base_dir is not None:
        configuration["global_data_dir"] = os.path.join(base_dir, "data")
    if configuration.get("shell_resource_bin_dir") is None and base_dir is not None:
        configuration["shell_resource_bin_dir"] = os.path.join(base_dir, "datagrowth", "resources", "shell", "bin")

    media_root = getattr(django_settings, "MEDIA_ROOT", None)
    if configuration.get("web_media_root") is None and media_root is not None:
        configuration["web_media_root"] = media_root


def build_default_configuration(project_location: Path | Literal["AUTODISCOVER"] | None = AUTODISCOVER,
                                django_settings: Any | None = None,
                                package_defaults: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """
    Create the final datagrowth namespaced defaults dictionary.

    Priority (highest to lowest):
    - invoke environment
    - invoke project datagrowth.yml
    - django namespaced settings
    - django plain compatibility settings
    - package defaults
    """
    # Check inputs and normalize
    django_settings = _get_django_settings(django_settings)
    if project_location not in (None, AUTODISCOVER) and not isinstance(project_location, Path):
        raise TypeError("project_location should be pathlib.Path, 'AUTODISCOVER', or None.")

    # Build Invoke config to guide loading and determine allowed keys
    invoke_config, nested_defaults = create_invoke_configuration(
        project_location=project_location,
        package_defaults=package_defaults
    )
    package_defaults = _flatten_package_defaults(nested_defaults)
    package_defaults["http_resource_user_agent"] = "DataGrowth (v{})".format(VERSION)
    project_allowed_keys = _infer_project_allowed_keys(getattr(invoke_config, "_project", {}))
    allowed_keys = set(package_defaults.keys())
    allowed_keys.update(project_allowed_keys)

    # Warn on source-specific unknown keys and identify which keys invoke actually overrides.
    project_layer = _normalize_namespaced(getattr(invoke_config, "_project", {}), allowed_keys, "invoke project")
    env_layer = _normalize_namespaced(getattr(invoke_config, "_env", {}), allowed_keys, "invoke env")
    invoke_overrides = merge_dicts(project_layer, env_layer)

    # Support implicit global env keys like DATAGROWTH_ASYNCHRONOUS.
    implicit_env: dict[str, Any] = {}
    prefix = "{}_".format(ENV_PREFIX)
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        if key in PLAIN_COMPATIBILITY_KEYS:
            continue
        env_key = key[len(prefix):].lower()
        if env_key in allowed_keys:
            continue
        normalized = "global_{}".format(env_key)
        if normalized not in allowed_keys:
            _warn_unknown("invoke env", key[len(prefix):])
            continue
        implicit_env[normalized] = _coerce_env_value(value, package_defaults.get(normalized))
    merge_dicts(invoke_overrides, implicit_env)

    # Finish the invoke layer
    merged_invoke = _normalize_namespaced(invoke_config, allowed_keys, "invoke")
    invoke_layer = {
        key: merged_invoke[key] if key in merged_invoke else value
        for key, value in invoke_overrides.items()
    }

    # Load Django settings layer as well as some legacy settings
    django_namespaced, django_plain = _django_override_layers(allowed_keys, django_settings=django_settings)

    configuration_hiarchy = [
        ("package defaults", package_defaults),
        ("django plain compatibility", django_plain),
        ("django settings", django_namespaced),
        ("invoke", invoke_layer),
    ]
    configuration: dict[str, Any] = {}
    for source, layer in configuration_hiarchy:
        merge_dicts(configuration, _validate_allowed(layer, allowed_keys, source))

    _apply_runtime_fallbacks(configuration, django_settings)
    return configuration
