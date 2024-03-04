from django.test import TestCase

from datatypes.tests.dataset import base as test_cases
from datatypes.models import FrozenDataset


class TestInitialDatasetFreezeStrategy(test_cases.InitialDatasetGrowthTestCase):
    dataset_model = FrozenDataset
    signature = "setting1=const&test"
    entity_type = "paper"


class TestContinuationDatasetFreezeStrategy(TestCase):

    def test_freeze_exception(self):
        self.skipTest("not implemented")

    def test_growth_limit(self):
        self.skipTest("not implemented")

    def test_growth_retry(self):
        self.skipTest("not implemented")

    def test_growth_revise(self):
        self.skipTest("not implemented")

    def test_new_task_definition(self):
        self.skipTest("not implemented")
