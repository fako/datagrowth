from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError

from datatypes.models import Document


class TestDocument(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.instance = Document.objects.get(id=1)
        self.value_outcome = "nested value 0"
        self.dict_outcome = {"value": "nested value 0"}
        self.expected_content = {
            'value': 'nested value 0',
            'context': 'nested value'
        }
        self.expected_items = sorted([('context', 'nested value'), ('value', 'nested value 0')])
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
        self.assertEqual(url, '/api/v1/datatypes/data/document/1/content/')
        self.instance.id = None
        try:
            url = self.instance.url
            self.fail("url property did not raise when id is not known")
        except ValueError:
            pass
        # Testing URL's with special class names
        class DocumentTest(Document):
            class Meta:
                app_label = "testing_apps"
        document_test = DocumentTest()
        document_test.id = 1
        with patch("datagrowth.datatypes.documents.db.base.reverse") as reverse_mock:
            url = document_test.url
            reverse_mock.assert_called_once_with("v1:testing-apps:document-test-content", args=[1])

    @patch("datagrowth.datatypes.DocumentBase.output_from_content")
    def test_output(self, output_from_content):
        self.instance.output("$.value")
        output_from_content.assert_called_once_with(self.instance.content, "$.value")

    def test_output_from_content(self):
        results = self.instance.output_from_content(self.instance.content, "$._id")
        self.assertEqual(results, self.instance.id)
        results = self.instance.output_from_content(self.instance.content, "$.value")
        self.assertEqual(results, self.value_outcome)
        results = self.instance.output_from_content(self.instance.content, "$.value", "$.value")
        self.assertEqual(list(results), [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, ["$.value"])
        self.assertEqual(results, [self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, ["$.value", "$.value"])
        self.assertEqual(list(results), [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, [])
        self.assertEqual(results, [])
        results = self.instance.output_from_content(self.instance.content, {"value": "$.value"})
        self.assertEqual(results, self.dict_outcome)
        results = self.instance.output_from_content(self.instance.content, [{"value": "$.value"}, {"value": "$.value"}])
        self.assertEqual(list(results), [self.dict_outcome, self.dict_outcome])
        results = self.instance.output_from_content(self.instance.content, {})
        self.assertEqual(results, {})

    def test_update(self):
        content = self.instance.update({"value": "nested value -1", "extra": "extra"})
        self.assertEqual(content["value"], "nested value -1")
        self.assertEqual(content["context"], "nested value")
        self.assertEqual(content["extra"], "extra")
        instance = Document.objects.get(id=1)
        self.assertEqual(instance.properties["value"], "nested value -1")
        self.assertEqual(instance.properties["context"], "nested value")
        self.assertEqual(instance.properties["extra"], "extra")

    @patch("jsonschema.validate")
    def test_validate(self, jsonschema_validate):
        Document.validate(self.instance, self.schema)
        jsonschema_validate.assert_called_with(self.instance.properties, self.schema)
        jsonschema_validate.reset_mock()
        Document.validate(self.instance.properties, self.schema)
        jsonschema_validate.assert_called_with(self.instance.properties, self.schema)
        jsonschema_validate.reset_mock()
        Document.validate(self.instance.content, self.schema)
        jsonschema_validate.assert_called_with(self.instance.properties, self.schema)
        jsonschema_validate.reset_mock()
        try:
            Document.validate([self.instance], self.schema)
        except ValidationError:
            jsonschema_validate.assert_not_called()

    def test_validate_error(self):
        wrong_content = self.instance.content
        wrong_content["wrong"] = True
        try:
            Document.validate(wrong_content, self.schema)
            self.fail("Document.validate did not raise upon wrong content")
        except ValidationError:
            pass
        Document.validate(wrong_content, {"bullshit": "schema"})

    @patch('datatypes.models.Collection.influence')
    def test_clean_without_collective(self, influence_method):
        self.instance.collection = None
        self.instance.clean()
        influence_method.assert_not_called()

    @patch('datatypes.models.Collection.influence')
    def test_clean_with_collective(self, influence_method):
        self.instance.clean()
        influence_method.assert_called_once_with(self.instance)

    def test_getitem(self):
        value = self.instance["value"]
        self.assertEqual(value, self.instance.properties["value"])

    def test_setitem(self):
        self.instance["value"] = "new value"
        self.assertEqual(self.instance.properties["value"], "new value")

    def test_items(self):
        items = sorted(list(self.instance.items()))
        self.assertEqual(items, self.expected_items)

    def test_keys(self):
        expected_keys, expected_values = zip(*self.expected_items)
        keys = tuple(sorted(self.instance.keys()))
        self.assertEqual(keys, expected_keys)

    def test_values(self):
        expected_keys, expected_values = zip(*self.expected_items)
        values = tuple(sorted(self.instance.values()))
        self.assertEqual(values, expected_values)
