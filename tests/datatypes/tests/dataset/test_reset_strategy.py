from django.test import TestCase

from datatypes.tests.dataset import base as test_cases
from datatypes.models import ResettingDataset


class TestInitialDatasetResetStrategy(test_cases.InitialDatasetGrowthTestCase):
    dataset_model = ResettingDataset
    signature = "setting1=const&test"
    entity_type = "paper"


class TestContinuationDatasetResetStrategy(TestCase):

    def test_growth_success(self):
        self.skipTest("not implemented")

    def test_growth_limit(self):
        self.skipTest("not implemented")

    def test_growth_retry(self):
        self.skipTest("not implemented")

    def test_seeding_error(self):
        self.skipTest("not implemented")

    def test_new_task_definition(self):
        self.skipTest("not implemented")
