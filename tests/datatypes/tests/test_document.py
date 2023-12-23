from unittest.mock import patch
from datetime import date

from django.test import TestCase
from django.core.exceptions import ValidationError

from datatypes.models import Document, Collection


class TestDocument(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.instance = Document.objects.get(id=1)
        self.value_outcome = "0"
        self.dict_outcome = {"value": "0"}
        self.expected_items = sorted([('context', 'nested value'), ('nested', 'nested value 0'), ('value', '0')])
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
        self.build_data = {
            "identifier": "identity",
            "referee": "reference",
            "value": "value"
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
        self.assertEqual(results, [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, ["$.value"])
        self.assertEqual(results, [self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, ["$.value", "$.value"])
        self.assertEqual(results, [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, {"value": "$.value"})
        self.assertEqual(results, self.dict_outcome)
        results = self.instance.output_from_content(self.instance.content, [{"value": "$.value"}, {"value": "$.value"}])
        self.assertEqual(results, [self.dict_outcome, self.dict_outcome])

    def test_output_from_content_replacement_character(self):
        results = self.instance.output_from_content(self.instance.content, "#._id", replacement_character="#")
        self.assertEqual(results, self.instance.id)
        results = self.instance.output_from_content(self.instance.content, "#.value", replacement_character="#")
        self.assertEqual(results, self.value_outcome)
        results = self.instance.output_from_content(
            self.instance.content, "#.value", "#.value",
            replacement_character="#"
        )
        self.assertEqual(results, [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(self.instance.content, ["#.value"], replacement_character="#")
        self.assertEqual(results, [self.value_outcome])
        results = self.instance.output_from_content(
            self.instance.content, ["#.value", "#.value"],
            replacement_character="#"
        )
        self.assertEqual(results, [self.value_outcome, self.value_outcome])
        results = self.instance.output_from_content(
            self.instance.content, {"value": "#.value"},
            replacement_character="#"
        )
        self.assertEqual(results, self.dict_outcome)
        results = self.instance.output_from_content(
            self.instance.content, [{"value": "#.value"}, {"value": "#.value"}],
            replacement_character="#"
        )
        self.assertEqual(results, [self.dict_outcome, self.dict_outcome])

    def test_output_from_content_no_replacement(self):
        results = self.instance.output_from_content(self.instance.content, "value")
        self.assertEqual(results, "value")
        results = self.instance.output_from_content(self.instance.content, "value", 1)
        self.assertEqual(results, ["value", 1])
        results = self.instance.output_from_content(self.instance.content, ["value"])
        self.assertEqual(results, ["value"])
        results = self.instance.output_from_content(self.instance.content, ["value", 1])
        self.assertEqual(results, ["value", 1])
        results = self.instance.output_from_content(self.instance.content, {"value": "value"})
        self.assertEqual(results, {"value": "value"})
        results = self.instance.output_from_content(self.instance.content, [{"value": "value"}, {"value": 1}])
        self.assertEqual(results, [{"value": "value"}, {"value": 1}])

    def test_output_from_content_empty_values(self):
        results = self.instance.output_from_content(self.instance.content, [])
        self.assertEqual(results, [])
        results = self.instance.output_from_content(self.instance.content, {})
        self.assertEqual(results, {})

    def test_output_from_content_escaped(self):
        results = self.instance.output_from_content(self.instance.content, r"\$.value")
        self.assertEqual(results, "$.value", "Expected escaped replacement_character to be passed along")
        results = self.instance.output_from_content(self.instance.content, r"\\$.value")
        self.assertEqual(results, r"\$.value", "Expected escaped backslash to be passed along")
        try:
            self.instance.output_from_content(self.instance.content, "$.value", replacement_character="\\")
            self.fail("Document.output_from_content did not raise AssertionError with invalid replacement_character")
        except AssertionError:
            pass

    def test_update_using_dict(self):
        created_at = self.instance.created_at
        today = date.today()
        content = self.instance.update({"value": "-1", "extra": "extra"})
        self.assertEqual(self.instance.created_at, created_at)
        self.assertNotEqual(self.instance.modified_at.date, today)
        self.assertEqual(content["value"], "-1")
        self.assertEqual(content["context"], "nested value")
        self.assertEqual(content["nested"], "nested value 0")
        self.assertEqual(content["extra"], "extra")
        instance = Document.objects.get(id=1)
        self.assertEqual(instance.properties["value"], "-1")
        self.assertEqual(instance.properties["context"], "nested value")
        self.assertEqual(instance.properties["nested"], "nested value 0")
        self.assertEqual(instance.properties["extra"], "extra")

    def test_update_using_doc(self):
        created_at = self.instance.created_at
        today = date.today()
        doc = Document.objects.create(properties={"value": "-1", "extra": "extra"})
        content = self.instance.update(doc)
        self.assertEqual(self.instance.created_at, created_at)
        self.assertNotEqual(self.instance.modified_at.date, today)
        self.assertEqual(content["value"], "-1")
        self.assertEqual(content["context"], "nested value")
        self.assertEqual(content["nested"], "nested value 0")
        self.assertEqual(content["extra"], "extra")
        instance = Document.objects.get(id=1)
        self.assertEqual(instance.properties["value"], "-1")
        self.assertEqual(instance.properties["context"], "nested value")
        self.assertEqual(instance.properties["nested"], "nested value 0")
        self.assertEqual(instance.properties["extra"], "extra")

    def test_update_no_commit(self):
        created_at = self.instance.created_at
        today = date.today()
        doc = Document.objects.create(properties={"value": "-1", "extra": "extra"})
        content = self.instance.update(doc, commit=False)
        self.assertEqual(self.instance.created_at, created_at)
        self.assertNotEqual(self.instance.modified_at.date, today)
        self.assertEqual(content["value"], "-1")
        self.assertEqual(content["context"], "nested value")
        self.assertEqual(content["nested"], "nested value 0")
        self.assertEqual(content["extra"], "extra")
        instance = Document.objects.get(id=1)
        self.assertEqual(instance.properties["value"], "0")
        self.assertEqual(instance.properties["context"], "nested value")
        self.assertEqual(instance.properties["nested"], "nested value 0")
        self.assertNotIn("extra", instance.properties)

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
        expected_values = tuple(sorted(expected_values))
        values = tuple(sorted(self.instance.values()))
        self.assertEqual(values, expected_values)

    def test_build_with_collection(self):
        collection = Collection.objects.create(name="build-test", identifier="identifier", referee="referee")
        build = Document.build(self.build_data, collection=collection)
        self.assertIsNone(build.id, "Did not expect a build to be created in the database")
        self.assertEqual(build.properties, self.build_data)
        self.assertEqual(build.reference, "reference")
        self.assertEqual(build.identity, "identity")

    def test_build(self):
        build = Document.build(self.build_data)
        self.assertIsNone(build.id, "Did not expect a build to be created in the database")
        self.assertEqual(build.properties, self.build_data)
        self.assertIsNone(build.reference, "Did not expect an implicit reference without a Collection")
        self.assertIsNone(build.identity, "Did not expect an implicit identity without a Collection")
