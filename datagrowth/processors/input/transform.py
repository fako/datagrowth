from datagrowth.configuration import ConfigurationProperty
from datagrowth.processors.input.extraction import ExtractProcessor


class TransformProcessor(ExtractProcessor):
    """
    This processor function like the ``ExtractProcessor``, but has a name that resembles its function a bit better.
    In the future the ``ExtractProcessor`` will be deprecated in favor of this ``TransformProcessor``.
    """

    config = ConfigurationProperty(
        storage_attribute="_config",
        private=["_objective"],
        namespace="transform_processor"
    )
