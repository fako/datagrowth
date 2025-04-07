from datagrowth.configuration import ConfigurationProperty
from datagrowth.processors.input.extraction import ExtractProcessor


class TransformProcessor(ExtractProcessor):

    config = ConfigurationProperty(
        storage_attribute="_config",
        private=["_objective"],
        namespace="transform_processor"
    )
