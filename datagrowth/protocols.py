from __future__ import annotations

from typing import Any, Protocol

from datagrowth.configuration import ConfigurationProperty, ConfigurationType


class ProcessorProtocol(Protocol):

    config: ConfigurationProperty

    @staticmethod
    def get_processor_components(processor_definition: str) -> tuple[str, str]:
        ...

    @staticmethod
    def create_processor(processor_name: str, config: ConfigurationType | dict[str, Any]) -> "ProcessorProtocol":
        ...

    @staticmethod
    def get_processor_class(processor_name: str) -> type["ProcessorProtocol"] | None:
        ...
