from django.test import TestCase
from django.apps import apps

from datagrowth.processors import (Processor, QuerySetProcessor, ExtractProcessor, GrowthProcessor, HttpGrowthProcessor,
                                   HttpSeedingProcessor)
from datagrowth.processors.base import ArgumentsTypes
from processors.processors import ProcessorMock
from datatypes.processors import DataProcessor


class TestDatagrowthProcessorDjangoConfig(TestCase):

    def setUp(self):
        super().setUp()
        self.config = apps.get_app_config("datagrowth")
        self.expected_processors = {
            # Datagrowth processors
            "Processor": Processor,
            "ExtractProcessor": ExtractProcessor,
            "QuerySetProcessor": QuerySetProcessor,
            "GrowthProcessor": GrowthProcessor,
            "HttpGrowthProcessor": HttpGrowthProcessor,
            "HttpSeedingProcessor": HttpSeedingProcessor,
            # Test processors
            "ProcessorMock": ProcessorMock,
            "DataProcessor": DataProcessor
        }

    def test_load_processors(self):
        self.config.load_processors()
        self.assertEqual(self.config.processors, self.expected_processors)

    def test_get_processor_class(self):
        self.assertEqual(self.config.get_processor_class("Processor"), Processor)
        self.assertEqual(self.config.get_processor_class("ProcessorMock"), ProcessorMock)
        self.assertIsNone(self.config.get_processor_class("DoesNotExist"))


class TestProcessorBase(TestCase):

    def setUp(self):
        super().setUp()
        self.processor = ProcessorMock(config={})

    def test_get_processor_components(self):
        processor_name, method_name = Processor.get_processor_components("ProcessorMock.default_method")
        self.assertEqual(processor_name, "ProcessorMock")
        self.assertEqual(method_name, "default_method")
        processor_name, method_name = Processor.get_processor_components("DoesNotExist.does_not_exist")
        self.assertEqual(processor_name, "DoesNotExist")
        self.assertEqual(method_name, "does_not_exist")
        try:
            Processor.get_processor_components("invalid")
            self.fail("Processor.get_processor_components did not raise when getting invalid processor name")
        except AssertionError:
            pass

    def test_create_processor(self):
        config = {"test": "test"}
        processor = Processor.create_processor("ProcessorMock", config)
        self.assertIsInstance(processor, ProcessorMock)
        self.assertEqual(processor.config.to_dict(), config)
        processor = Processor.create_processor("ProcessorMock", {})
        self.assertIsInstance(processor, ProcessorMock)
        self.assertEqual(processor.config.to_dict(), {})
        try:
            Processor.create_processor("ProcessorMock", None)
            self.fail("Processor.create_processor did not raise when getting invalid config")
        except AssertionError:
            pass
        try:
            Processor.create_processor("DoesNotExist", config)
            self.fail("Processor.create_processor did not raise when getting missing processor name")
        except AssertionError:
            pass
        try:
            Processor.create_processor("invalid", config)
            self.fail("Processor.create_processor did not raise when getting invalid processor name")
        except AssertionError:
            pass

    def test_get_processor_method(self):
        method, method_type = self.processor.get_processor_method("normal_method")
        self.assertEqual(method, self.processor.normal_method)
        self.assertEqual(method_type, ArgumentsTypes.NORMAL)
        method, method_type = self.processor.get_processor_method("batch_method")
        self.assertEqual(method, self.processor.batch_method)
        self.assertEqual(method_type, ArgumentsTypes.BATCH)
        method, method_type = self.processor.get_processor_method("default_method")
        self.assertEqual(method, self.processor.default_method)
        self.assertEqual(method_type, self.processor.DEFAULT_ARGS_TYPE)

    def test_get_processor_class(self):
        self.assertEqual(Processor.get_processor_class("Processor"), Processor)
        self.assertEqual(Processor.get_processor_class("ProcessorMock"), ProcessorMock)
        self.assertIsNone(Processor.get_processor_class("DoesNotExist"))
