from django.test import TestCase

from datagrowth.configuration import create_config
from datagrowth.datatypes.documents.tasks.collection import grow_collection

from datatypes.models import DatasetVersion, Collection, Document


class TestGrowCollection(TestCase):

    fixtures = ["test-dataset"]

    def setUp(self):
        self.config = create_config("global", {})
        self.collection = Collection.objects.get(id=1)

    def test_grow_collection(self):
        grow_collection("datatypes.Collection", self.collection.id, "paper", config=self.config, asynchronous=False)
        self.assertEqual(Document.objects.count(), 6 + 20, "Expected twenty new Documents and six unchanged Documents")
        self.assertEqual(Collection.objects.count(), 3, "Expected three unchanged Collections")
        self.assertEqual(DatasetVersion.objects.count(), 3, "Expected three unchanged DatasetVersions")
