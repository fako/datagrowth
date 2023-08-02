import os
import json
from unittest.mock import patch, MagicMock, NonCallableMagicMock
from datetime import date
from types import GeneratorType

from django.test import TestCase

from datatypes.models import Collection, Document


class TestCollection(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.instance = Collection.objects.get(id=1)
        self.instance2 = Collection.objects.get(id=2)
        self.document = Document.objects.get(id=4)
        self.value_outcome = ["0", "1", "2"]
        self.list_outcome = [["0"], ["1"], ["2"]]
        self.double_list_outcome = [
            ["0", "0"],
            ["1", "1"],
            ["2", "2"]
        ]
        self.dict_outcome = [{"value": "0"}, {"value": "1"}, {"value": "2"}]
        self.expected_content = [
            {"context": "nested value", "value": "0"},
            {"context": "nested value", "value": "1"},
            {"context": "nested value", "value": "2"}
        ]
        self.schema = {
            "additionalProperties": False,
            "required": ["value"],
            "type": "object",
            "properties": {
                "word": {"type": "string"},
                "value": {"type": "string"},
                "language": {"type": "string"},
                "country": {"type": "string"}
            }
        }

    def test_url(self):
        # Testing standard URL's
        url = self.instance.url
        self.assertEqual(url, '/api/v1/datatypes/data/collection/1/content/')
        self.instance.id = None
        try:
            url = self.instance.url
            self.fail("url property did not raise when id is not known")
        except ValueError:
            pass
        # Testing URL's with special class names
        class CollectionTest(Collection):
            class Meta:
                app_label = "testing_apps"
        collection_test = CollectionTest()
        collection_test.id = 1
        with patch("datagrowth.datatypes.documents.db.base.reverse") as reverse_mock:
            url = collection_test.url
            reverse_mock.assert_called_once_with("v1:testing-apps:collection-test-content", args=[1])

    @patch('datatypes.models.Document.validate')
    def test_validate_queryset(self, validate_method):
        self.instance.validate(self.instance.documents.all(), self.schema)
        for doc in self.instance.documents.all():
            validate_method.assert_any_call(doc, self.schema)

    @patch('datatypes.models.Document.validate')
    def test_validate_content(self, validate_method):
        self.instance.validate(self.instance.content, self.schema)
        for doc in self.instance.content:
            validate_method.assert_any_call(doc, self.schema)

    def get_docs_list_and_ids(self, value=None):
        docs = []
        doc_ids = []
        for index, doc in enumerate(self.instance2.documents.all()):
            doc_ids.append(doc.id)
            if value:
                doc.properties["value"] = value
            docs.append(doc) if index % 2 else docs.append(doc.properties)
        return docs, doc_ids

    @patch('datatypes.models.Collection.influence')
    def test_add(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids(value="value 3")
        today = date.today()
        created_at = self.instance2.created_at
        with self.assertNumQueries(3):
            # Query 1: reset
            # Query 2: insert documents
            # Query 3: update modified_at
            self.instance2.add(docs, reset=True)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance2.documents.count(), 5)
        self.assertEqual(self.instance2.created_at, created_at)
        self.assertEqual(self.instance2.modified_at.date(), today)
        for doc in self.instance2.documents.all():
            self.assertEqual(doc.properties["value"], "value 3")
            self.assertIsNotNone(doc.created_at)
            self.assertIsNotNone(doc.modified_at)
            self.assertNotIn(doc.id, doc_ids)

    @patch('datatypes.models.Collection.influence')
    def test_add_no_reset(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids(value="5")
        today = date.today()
        created_at = self.instance2.created_at
        with self.assertNumQueries(2):  # query set cache is filled, -1 query
            # NB: no reset
            # Query 1: insert documents
            # Query 2: update modified_at
            self.instance2.add(docs, reset=False)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance2.documents.count(), 10)
        self.assertEqual(self.instance2.created_at, created_at)
        self.assertEqual(self.instance2.modified_at.date(), today)
        new_ids = []
        for doc in self.instance2.documents.all():
            self.assertIn(doc.properties["value"], ["1", "2", "3", "4", "5"])
            self.assertIsNotNone(doc.created_at)
            self.assertIsNotNone(doc.modified_at)
            new_ids.append(doc.id)
        for id_value in doc_ids:
            self.assertIn(id_value, new_ids)

    def test_add_batch(self):
        docs = list(self.instance2.documents.all()) * 5
        with self.assertNumQueries(4):
            add_batches = self.instance2.add_batches(docs, reset=True, batch_size=20)
            self.assertIsInstance(add_batches, GeneratorType)
            for batch in add_batches:
                self.assertIsInstance(batch, list)
                for doc in batch:
                    self.assertIsInstance(doc, Document)
        self.assertEqual(self.instance2.documents.count(), 25)

    @patch('datatypes.models.Collection.influence')
    def test_copy_add(self, influence_method):
        docs, original_ids = self.get_docs_list_and_ids("copy")
        self.instance.add(docs, reset=False)
        self.assertEqual(self.instance.documents.count(), 8)
        for doc in self.instance.documents.all():
            self.assertNotIn(doc.id, original_ids)
        self.assertEqual(self.instance.documents.exclude(pk__in=[1, 2, 3]).count(), len(original_ids))
        for args, kwargs in influence_method.call_args_list:
            self.assertEqual(len(args), 1)
            self.assertIsInstance(args[0], Document)
            self.assertEqual(kwargs, {})
        self.assertEqual(
            influence_method.call_count, len(original_ids),
            "Collection should only influence new Documents when updating"
        )

    @patch('datatypes.models.Collection.influence')
    def test_update(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids()
        today = date.today()
        created_at = self.instance.created_at
        with self.assertNumQueries(4):
            # Query 1: fetch targets
            # Query 2: update sources
            # Query 3: add sources
            # Query 4: update modified_at
            self.instance.update(docs, "value")
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance.documents.count(), 5)
        self.assertEqual(self.instance.created_at, created_at)
        self.assertEqual(self.instance.modified_at.date(), today)
        for doc in self.instance.documents.all():
            if doc.properties["value"] == "0":
                expected_keys = tuple(sorted(["value", "nested", "context"]))
            elif doc.properties["value"] == "1":
                expected_keys = tuple(sorted(["value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] == "2":
                expected_keys = tuple(sorted(["_id", "value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] in ["3", "4"]:
                expected_keys = tuple(sorted(["word", "country", "value", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            else:
                self.fail(f"Unexpected property 'value':{doc.properties['value']}")
            self.assertEqual(tuple(sorted(doc.keys())), expected_keys)
            self.assertNotIn(doc.id, doc_ids)

    @patch('datatypes.models.Collection.influence')
    def test_update_batch(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids()
        today = date.today()
        created_at = self.instance.created_at
        with self.assertNumQueries(8):
            # Batch 1: select + update
            # Batch 2: select + update + insert
            # Batch 3: select + insert
            # Query 8: update modified_at
            update_batches = self.instance.update_batches(docs, "value", batch_size=2)
            self.assertIsInstance(update_batches, GeneratorType)
            for batch in update_batches:
                self.assertIsInstance(batch, list)
                for doc in batch:
                    self.assertIsInstance(doc, Document)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance.documents.count(), 5)
        self.assertEqual(self.instance.created_at, created_at)
        self.assertEqual(self.instance.modified_at.date(), today)
        for doc in self.instance.documents.all():
            if doc.properties["value"] == "0":
                expected_keys = tuple(sorted(["value", "nested", "context"]))
            elif doc.properties["value"] == "1":
                expected_keys = tuple(sorted(["value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] == "2":
                expected_keys = tuple(sorted(["_id", "value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] in ["3", "4"]:
                expected_keys = tuple(sorted(["word", "country", "value", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            else:
                self.fail(f"Unexpected property 'value':{doc.properties['value']}")
            self.assertEqual(tuple(sorted(doc.keys())), expected_keys)
            self.assertNotIn(doc.id, doc_ids)

    @patch('datatypes.models.Collection.influence')
    def test_update_other_collection(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids()
        today = date.today()
        created_at = self.instance.created_at
        with self.assertNumQueries(4):
            # Query 1: fetch targets
            # Query 2: update sources
            # Query 3: add sources
            # Query 4: update modified_at
            self.instance2.update(docs, "value", collection=self.instance)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance.documents.count(), 5)
        self.assertEqual(self.instance.created_at, created_at)
        self.assertEqual(self.instance.modified_at.date(), today)
        for doc in self.instance.documents.all():
            if doc.properties["value"] == "0":
                expected_keys = tuple(sorted(["value", "nested", "context"]))
            elif doc.properties["value"] == "1":
                expected_keys = tuple(sorted(["value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] == "2":
                expected_keys = tuple(sorted(["_id", "value", "nested", "context", "word", "country", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            elif doc.properties["value"] in ["3", "4"]:
                expected_keys = tuple(sorted(["word", "country", "value", "language"]))
                self.assertEqual(doc.modified_at.date(), today)
            else:
                self.fail(f"Unexpected property 'value':{doc.properties['value']}")
            self.assertEqual(tuple(sorted(doc.keys())), expected_keys)
            self.assertNotIn(doc.id, doc_ids)

    def test_output(self):
        results = self.instance.output("$.value")
        self.assertEqual(results, self.value_outcome)
        results = self.instance.output("$.value", "$.value")
        self.assertEqual(list(results), [self.value_outcome, self.value_outcome])
        results = self.instance.output(["$.value"])
        self.assertEqual(results, self.list_outcome)
        results = self.instance.output(["$.value", "$.value"])
        self.assertEqual(results, self.double_list_outcome)
        results = self.instance.output([])
        self.assertEqual(results, [[], [], []])
        results = self.instance.output({"value": "$.value"})
        self.assertEqual(results, self.dict_outcome)
        results = self.instance.output({})
        self.assertEqual(results, [{}, {}, {}])

    def create_documents_mock(self, docs, total):
        queryset = NonCallableMagicMock()
        queryset.order_by = MagicMock(return_value=queryset)
        queryset.iterator = MagicMock(return_value=iter(docs))
        queryset.count = MagicMock(return_value=total)
        return queryset

    def test_split_content(self):
        # Standard version
        documents_mock = self.create_documents_mock(self.instance2.documents.all(), 5)
        with patch("datatypes.models.Collection.documents", documents_mock):
            train, validate, test = self.instance2.split()
            self.assertEqual(len(validate), 1)
            self.assertIsInstance(validate[0], Document)
            self.assertEqual(validate[0]["value"], "2")
            self.assertEqual(len(test), 1)
            self.assertIsInstance(test[0], Document)
            self.assertEqual(test[0]["value"], "1")
            for value in ["1", "3", "4"]:
                train_doc = next(train)
                self.assertIsInstance(train_doc, Document)
                self.assertEqual(train_doc["value"], value)
            try:
                next(train)
                self.fail("Training iterator had more content than expected")
            except StopIteration:
                pass
        # No test set
        documents_mock = self.create_documents_mock(self.instance2.documents.all(), 5)
        with patch("datatypes.models.Collection.documents", documents_mock):
            train, validate, test = self.instance2.split(train=0.6, validate=0.4, test=0)
            self.assertEqual(len(validate), 2)
            for ix, value in enumerate(["1", "2"]):
                validate_doc = validate[ix]
                self.assertIsInstance(validate_doc, Document)
                self.assertEqual(validate_doc["value"], value)
            for value in ["1", "3", "4"]:
                train_doc = next(train)
                self.assertIsInstance(train_doc, Document)
                self.assertEqual(train_doc["value"], value)
            try:
                next(train)
                self.fail("Training iterator had more content than expected")
            except StopIteration:
                pass
        # As content
        documents_mock = self.create_documents_mock(self.instance2.documents.all(), 5)
        with patch("datatypes.models.Collection.documents", documents_mock):
            train, validate, test = self.instance2.split()
            self.assertEqual(len(validate), 1)
            self.assertIsInstance(validate[0], Document)
            self.assertEqual(validate[0]["value"], "2")
            self.assertEqual(len(test), 1)
            self.assertIsInstance(test[0], Document)
            self.assertEqual(test[0]["value"], "1")
            for value in ["1", "3", "4"]:
                train_doc = next(train)
                self.assertIsInstance(train_doc, Document)
                self.assertEqual(train_doc["value"], value)
            try:
                next(train)
                self.fail("Training iterator had more content than expected")
            except StopIteration:
                pass
        # External queryset
        documents_mock = self.create_documents_mock(self.instance2.documents.all(), 5)
        train, validate, test = self.instance2.split(query_set=documents_mock)
        self.assertEqual(len(validate), 1)
        self.assertIsInstance(validate[0], Document)
        self.assertEqual(validate[0]["value"], "2")
        self.assertEqual(len(test), 1)
        self.assertIsInstance(test[0], Document)
        self.assertEqual(test[0]["value"], "1")
        for value in ["1", "3", "4"]:
            train_doc = next(train)
            self.assertIsInstance(train_doc, Document)
            self.assertEqual(train_doc["value"], value)
        try:
            next(train)
            self.fail("Training iterator had more content than expected")
        except StopIteration:
            pass

    def test_group_by(self):
        groups = self.instance2.group_by("country")
        for country, docs in groups.items():
            for doc in docs:
                self.assertEqual(doc.properties["country"], country)

    def test_influence(self):
        self.document.identity = None
        self.instance2.influence(self.document)
        self.assertEqual(self.document.identity, self.document.properties["word"])
        self.instance2.identifier = "country"
        self.instance2.influence(self.document)
        self.assertEqual(self.document.identity, self.document.properties["country"])
        self.instance2.identifier = None
        self.instance2.influence(self.document)
        self.assertEqual(self.document.identity, self.document.properties["country"])
        self.instance2.identifier = "does-not-exist"
        self.instance2.influence(self.document)
        self.assertIsNone(self.document.identity)

    def test_to_file(self):
        self.instance.to_file("test.json")
        with open("test.json", "r") as json_file:
            content = json.load(json_file)
        self.assertEqual(list(self.instance.content), content)
        os.remove("test.json")
