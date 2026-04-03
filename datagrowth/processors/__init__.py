# This file implements a lazy loading pattern to prevent Django from being imported too often.
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datagrowth.processors.base import Processor, ProcessorFactory
    from datagrowth.processors.growth import GrowthProcessor
    from datagrowth.processors.input import (
        ExtractProcessor,
        HttpSeedingProcessor,
        SeedingProcessorFactory,
        TransformProcessor,
    )
    from datagrowth.processors.resources.growth import HttpGrowthProcessor


__all__ = [
    "Processor",
    "ProcessorFactory",
    "GrowthProcessor",
    "ExtractProcessor",
    "TransformProcessor",
    "HttpSeedingProcessor",
    "SeedingProcessorFactory",
    "HttpGrowthProcessor",
]


def __getattr__(name: str) -> Any:
    if name in {"Processor", "ProcessorFactory"}:
        from datagrowth.processors.base import Processor as _Processor, ProcessorFactory as _ProcessorFactory
        return {
            "Processor": _Processor,
            "ProcessorFactory": _ProcessorFactory,
        }[name]

    if name == "GrowthProcessor":
        from datagrowth.processors.growth import GrowthProcessor as _GrowthProcessor
        return _GrowthProcessor

    if name in {"ExtractProcessor", "TransformProcessor", "HttpSeedingProcessor", "SeedingProcessorFactory"}:
        from datagrowth.processors.input import (
            ExtractProcessor as _ExtractProcessor,
            HttpSeedingProcessor as _HttpSeedingProcessor,
            SeedingProcessorFactory as _SeedingProcessorFactory,
            TransformProcessor as _TransformProcessor,
        )
        return {
            "ExtractProcessor": _ExtractProcessor,
            "TransformProcessor": _TransformProcessor,
            "HttpSeedingProcessor": _HttpSeedingProcessor,
            "SeedingProcessorFactory": _SeedingProcessorFactory,
        }[name]

    if name == "HttpGrowthProcessor":
        from datagrowth.processors.resources.growth import HttpGrowthProcessor as _HttpGrowthProcessor
        return _HttpGrowthProcessor

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
