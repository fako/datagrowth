from unittest.mock import patch

from django.test import override_settings

from datagrowth.datatypes.datasets.constants import GrowthState
from datagrowth.datatypes.documents.tasks.document import dispatch_data_storage_tasks

from datatypes.tests.dataset import base as test_cases
from datatypes.models import DatasetPile, Document
from resources.models import EntityListResource


DISPATCH_DATA_STORAGE_TARGET = "datagrowth.datatypes.documents.tasks.document.dispatch_data_storage_tasks"


class TestInitialDatasetStackStrategy(test_cases.InitialDatasetGrowthTestCase):

    dataset_model = DatasetPile
    signature = "test"
    entity_type = "paper"
    use_current_version = False


class TestContinuationDatasetStackStrategy(test_cases.BaseDatasetGrowthTestCase):

    dataset_model = DatasetPile
    signature = "setting1=const&test"
    entity_type = "paper"
    use_current_version = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.create_historic_dataset_version()

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    @patch.object(EntityListResource, "PARAMETERS", {"size": 3, "page_size": 10})
    def test_growth_success(self, dispatch_mock):
        # Prepare test data
        remaining_title = "This title should remain the same in historic data."
        self.prepare_documents(properties={
            "2": {"title": remaining_title},
        })
        # Execute growth
        self.dataset.grow(self.entity_type, asynchronous=False)
        # Standard assertions
        self.assert_grow_success(dataset_versions=2, collections=2, documents=23)
        self.assert_dataset_output(self.dataset, dataset_versions=2, collections=2, documents=23)
        self.assert_dataset_finish()
        self.assert_document_dispatch(dispatch_mock, ["0", "1", "2"])
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 1,
            "Expected remaining title to be present in historic data only."
        )

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    def test_growth_limit(self, dispatch_mock):
        # Prepare test data
        remaining_title = "This title should remain the same in historic data."
        self.prepare_documents(properties={
            "2": {"title": remaining_title},
        })
        # This test sets the limit to 3.
        # However the batch_size is 5 and therefor we expect to grow 5 Documents.
        self.dataset.grow(self.entity_type, asynchronous=False, limit=3)
        # Standard assertions
        self.assert_grow_success(dataset_versions=2, collections=2, documents=25)
        self.assert_dataset_output(self.dataset, dataset_versions=2, collections=2, documents=25)
        self.assert_dataset_finish()
        self.assert_document_dispatch(dispatch_mock, ["0", "1", "2", "3", "4"])
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 1,
            "Expected remaining title to be present in historic data only."
        )

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    def test_seeding_error(self, dispatch_mock):
        # Prepare test data
        remaining_title = "This title should remain the same in historic data."
        self.prepare_documents(properties={
            "2": {"title": remaining_title}
        })
        # Execute growth
        self.dataset.grow("does_not_exist", asynchronous=False)
        # Standard assertions
        self.assert_grow_success(dataset_versions=2, collections=2, documents=20)
        self.assert_dataset_output(self.dataset, dataset_versions=2, collections=2, documents=20)
        self.assert_dataset_finish()
        self.assertEqual(dispatch_mock.call_count, 0, "Did not expect Document tasks to get dispatched")
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 1,
            "Expected remaining title to be present in historic data only."
        )
        entity_list_resource = EntityListResource.objects.last()
        dataset_version = self.dataset.get_current_dataset_version()
        self.assertEqual(dataset_version.errors, {
            "tasks": {
                "check_doi": {
                    "fail": 0,
                    "skipped": 0,
                    "success": 0
                }
            },
            "seeding": {
                "resources.entitylistresource": {
                    "id": entity_list_resource.id,
                    "ids": [entity_list_resource.id],
                    "success": False,
                    "resource": "resources.entitylistresource"
                }
            }
        })

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    def test_task_error(self, dispatch_mock):
        # Prepare test data
        remaining_title = "This title should remain the same in historic data."
        self.prepare_documents(
            properties={"2": {"title": remaining_title}},
            task_results={
                # this task_results should be overwritten and is retried with a failure
                "1": {"check_doi": {"success": False}},
                # these task_results should be overwritten and are retried successfully
                "2": {"check_doi": {"success": False}},
                "4": {"check_doi": {"success": False}}
            }
        )
        # Execute growth
        with override_settings(TEST_CHECK_DOI_FAILURE_IDENTITIES=["1"]):
            self.dataset.grow(self.entity_type, asynchronous=False)
        # Standard assertions
        # There are four error documents, because three historic documents are not retried
        # and one new document still fails.
        self.assert_grow_failure(dataset_versions=2, collections=2, documents=36, error_documents=4)
        self.assert_dataset_output(self.dataset, dataset_versions=2, collections=2, documents=40)
        self.assert_dataset_finish()
        self.assert_document_dispatch(dispatch_mock, [str(ix) for ix in range(0, 20)])  # dispatching all new documents
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 1,
            "Expected remaining title to be present in historic data only."
        )
        dataset_version = self.dataset.get_current_dataset_version()
        self.assertEqual(dataset_version.errors, {
            "tasks": {
                "check_doi": {
                    "fail": 1,
                    "skipped": 0,
                    "success": 19
                }
            },
            "seeding": {}
        })

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    def test_growth_retry(self, dispatch_mock):
        # Set the historic dataset version to ERROR
        dataset_version = self.dataset.get_current_dataset_version()
        dataset_version.state = GrowthState.ERROR
        dataset_version.save()
        # Prepare test data
        remaining_title = "This title should remain. New data is never fetched during a retry with historic data"
        self.prepare_documents(
            properties={
                "2": {"title": remaining_title},
                "4": {"title": remaining_title}
            },
            task_results={
                # these task_results should be overwritten and are retried successfully
                "1": {"check_doi": {"success": False}},
                "2": {"check_doi": {"success": False}},
                "4": {"check_doi": {"success": False}}
            }
        )
        # Execute growth
        self.dataset.grow(self.entity_type, retry=True, asynchronous=False)
        # Standard assertions
        self.assert_grow_success(dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_finish()
        self.assert_document_dispatch(dispatch_mock, ["1", "2", "4"])
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 2,
            "Expected remaining title to be present in historic data only."
        )
        dataset_version = self.dataset.get_current_dataset_version()
        self.assertEqual(dataset_version.errors, {
            "tasks": {
                "check_doi": {
                    "fail": 0,
                    "skipped": 0,
                    "success": 20
                }
            },
            "seeding": {}
        })

    @patch(DISPATCH_DATA_STORAGE_TARGET, side_effect=dispatch_data_storage_tasks)
    def test_growth_retry_completed(self, dispatch_mock):
        # Completed DatasetVersions should simply trigger a normal growth
        # Prepare test data
        remaining_title = "This title should remain the same in historic data."
        self.prepare_documents(
            properties={
                "2": {"title": remaining_title},
                "4": {"title": remaining_title}
            },
            task_results={
                # These task_results should be overwritten for new data and get retried
                "1": {"check_doi": {"success": False}},
                "2": {"check_doi": {"success": False}},
                "4": {"check_doi": {"success": False}}
            }
        )
        # Execute growth where retry is not fetching documents, but does create copies and retries tasks
        self.dataset.grow(self.entity_type, retry=True, asynchronous=False)
        # Standard assertions
        self.assert_grow_failure(dataset_versions=2, collections=2, documents=37, error_documents=3)
        self.assert_dataset_output(self.dataset, dataset_versions=2, collections=2, documents=40)
        self.assert_dataset_finish()
        self.assert_document_dispatch(dispatch_mock, [str(ix) for ix in range(0, 20)])  # dispatching all new documents
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 2,
            "Expected remaining title to be present in historic data only."
        )
        dataset_version = self.dataset.get_current_dataset_version()
        self.assertEqual(dataset_version.errors, {
            "tasks": {
                "check_doi": {
                    "fail": 0,
                    "skipped": 0,
                    "success": 20
                }
            },
            "seeding": {}
        })
