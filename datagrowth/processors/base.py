from django.apps import apps

from datagrowth.configuration import ConfigurationProperty, ConfigurationType


class ArgumentsTypes:
    NORMAL = 'normal'
    BATCH = 'batch'


class Processor(object):
    """
    This class is the base class for all processors.
    All processors have a config attribute that contains the configuration for the ``Processor``.

    For the rest the base class mainly provides the ``create_processor`` and ``get_processor_class`` class methods.
    Any class inheriting from ``Processor`` can be loaded through these methods by its name.
    This is useful when you want to transfer the ``Processor`` without transferring the actual callables,
    because most transportation formats (like JSON) don't support callables.
    """

    DEFAULT_ARGS_TYPE = ArgumentsTypes.NORMAL
    ARGS_NORMAL_METHODS = []
    ARGS_BATCH_METHODS = []

    config = ConfigurationProperty()

    def __init__(self, config):
        assert isinstance(config, (dict, ConfigurationType)), "Processor expects to get a configuration."
        self.config = config

    @staticmethod
    def get_processor_components(processor_definition):
        try:
            processor_name, method_name = processor_definition.split(".")
            return processor_name, method_name
        except ValueError:
            raise AssertionError(
                "Processor definition should be a dotted string "
                "in the form of 'class.method' got '{}' instead".format(processor_definition)
            )

    @staticmethod
    def create_processor(processor_name, config):
        """
        This method will load the Processor class given by name and instantiate it with the given configuration.

        :param processor_name: (str) the Processor to load
        :param config: (ConfigurationType or dict) the configuration to instantiate the Processor with
        :return:
        """
        processor_class = Processor.get_processor_class(processor_name)
        if processor_class is None:
            raise AssertionError(
                "Could not import a processor named {} from any processors module.".format(processor_name)
            )
        return processor_class(config=config)

    def get_processor_method(self, method_name):
        if method_name in self.ARGS_NORMAL_METHODS:
            args_type = ArgumentsTypes.NORMAL
        elif method_name in self.ARGS_BATCH_METHODS:
            args_type = ArgumentsTypes.BATCH
        else:
            args_type = self.DEFAULT_ARGS_TYPE
        return getattr(self, method_name), args_type

    @staticmethod
    def get_processor_class(processor_name):
        """
        This method will load the Processor class given by name and return it.
        If the Processor does not exist in an installed app it will return None instead

        :param processor_name: (str) the Processor to load
        :return: (class or None) the Processor class
        """
        datagrowth_config = apps.get_app_config("datagrowth")
        return datagrowth_config.get_processor_class(processor_name)


class QuerySetProcessor(Processor):
    pass
