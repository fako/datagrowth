import argparse
from functools import wraps
from typing import Any, Callable, Sequence, TypeVar
from urllib.parse import parse_qsl

from datagrowth.configuration.types import ConfigurationType


F = TypeVar("F", bound=Callable[..., Any])


def load_config() -> Callable[[F], F]:
    """
    This decorator will turn the value of any keyword arguments named "config" into a ConfigurationType.
    The decorated function will get the configuration as its first argument.

    :return: Wrapped function
    """
    def wrap(func: F) -> F:
        @wraps(func)
        def config_func(*args: Any, **kwargs: Any) -> Any:
            config = kwargs.pop("config", {})
            if not config:
                raise TypeError("load_config decorator expects a config kwarg.")
            if not isinstance(config, dict):
                return func(config, *args, **kwargs)
            config_instance = ConfigurationType.from_dict(config)
            return func(config_instance, *args, **kwargs)
        return config_func  # type: ignore[return-value]
    return wrap


class DecodeConfigAction(argparse.Action):
    """
    This class can be used as action for any argsparse command line option (like Django management command options).
    It will parse a URL like parameter string into a dictionary. This dictionary can then be used to initialize
    a configuration.
    """

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace,
                 values: str | Sequence[Any] | None, option_string: str | None = None) -> None:
        if not isinstance(values, str):
            raise TypeError("DecodeConfigAction expects a string value, got {!r}".format(values))
        parsed = dict(parse_qsl(values))
        setattr(namespace, self.dest, parsed)
