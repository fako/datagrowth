
from unittest.mock import patch

from django.test import TransactionTestCase

from datatypes.models import Collection, Document


class TestCollection(TransactionTestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.instance = Collection.objects.get(id=1)
        self.instance2 = Collection.objects.get(id=2)
        self.document = Document.objects.get(id=4)
        self.value_outcome = ["nested value 0", "nested value 1", "nested value 2"]
        self.list_outcome = [["nested value 0"], ["nested value 1"], ["nested value 2"]]
        self.double_list_outcome = [
            ["nested value 0", "nested value 0"],
            ["nested value 1", "nested value 1"],
            ["nested value 2", "nested value 2"]
        ]
        self.dict_outcome = [{"value": "nested value 0"}, {"value": "nested value 1"}, {"value": "nested value 2"}]
        self.expected_content = [
            {"context": "nested value", "value": "nested value 0"},
            {"context": "nested value", "value": "nested value 1"},
            {"context": "nested value", "value": "nested value 2"}
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
        url = self.instance.url
        self.assertEqual(url, '/data/v1/Collection/1/content/')
        self.instance.id = None
        try:
            url = self.instance.url
            self.fail("url property did not raise when id is not known")
        except ValueError:
            pass

    @patch('datatypes.models.Document.validate')
    def test_validate_queryset(self, validate_method):
        self.instance.validate(self.instance.document_set.all(), self.schema)
        for doc in self.instance.document_set.all():
            validate_method.assert_any_call(doc, self.schema)

    @patch('datatypes.models.Document.validate')
    def test_validate_content(self, validate_method):
        self.instance.validate(self.instance.content, self.schema)
        for doc in self.instance.content:
            validate_method.assert_any_call(doc, self.schema)

    def get_docs_list_and_ids(self, value):
        docs = []
        doc_ids = []
        for index, doc in enumerate(self.instance2.document_set.all()):
            doc_ids.append(doc.id)
            doc.properties["value"] = value
            docs.append(doc) if index % 2 else docs.append(doc.properties)
        return docs, doc_ids

    @patch('datatypes.models.Collection.influence')
    def test_add(self, influence_method):
        docs, doc_ids = self.get_docs_list_and_ids(value="value 3")
        with self.assertNumQueries(2):
            # Query 1: reset
            # Query 2: insert documents
            self.instance2.add(docs, reset=True)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance2.document_set.count(), 5)
        for doc in self.instance2.document_set.all():
            self.assertEqual(doc.properties["value"], "value 3")
            self.assertNotIn(doc.id, doc_ids)

        influence_method.reset_mock()
        docs, doc_ids = self.get_docs_list_and_ids(value="value 4")
        with self.assertNumQueries(2):
            # Query 1: reset
            # Query 2: insert documents
            self.instance2.add(docs, reset=True)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance2.document_set.count(), 5)
        for doc in self.instance2.document_set.all():
            self.assertEqual(doc.properties["value"], "value 4")
            self.assertNotIn(doc.id, doc_ids)

        influence_method.reset_mock()
        docs, doc_ids = self.get_docs_list_and_ids(value="value 5")
        with self.assertNumQueries(1):  # query set cache is filled, -1 query
            # NB: no reset
            # Query 1: insert documents
            self.instance2.add(docs, reset=False)
        self.assertEqual(influence_method.call_count, 5)
        self.assertEqual(self.instance2.document_set.count(), 10)
        new_ids = []
        for doc in self.instance2.document_set.all():
            self.assertIn(doc.properties["value"], ["value 4", "value 5"])
            new_ids.append(doc.id)
        for id_value in doc_ids:
            self.assertIn(id_value, new_ids)

    def test_add_batch(self):
        docs = list(self.instance2.document_set.all()) * 5
        with self.assertNumQueries(3):
            self.instance2.add(docs, reset=True, batch_size=20)
        self.assertEqual(self.instance2.document_set.count(), 25)

    @patch('datatypes.models.Collection.influence')
    def test_copy_add(self, influence_method):
        docs, original_ids = self.get_docs_list_and_ids("copy")
        self.instance.add(docs, reset=False)
        self.assertEqual(self.instance.document_set.count(), 8)
        for ind in self.instance.document_set.all():
            self.assertNotIn(ind.id, original_ids)
        self.assertEqual(self.instance.document_set.exclude(pk__in=[1, 2, 3]).count(), len(original_ids))
        for args, kwargs in influence_method.call_args_list:
            self.assertEqual(len(args), 1)
            self.assertIsInstance(args[0], Document)
            self.assertEqual(kwargs, {})
        self.assertEqual(
            influence_method.call_count, len(original_ids),
            "Collection should only influence new Documents when updating"
        )

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

    def test_split_content(self):
        self.skipTest("not tested")

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
        self.skipTest("not tested")
