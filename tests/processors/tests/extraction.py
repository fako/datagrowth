from bs4 import BeautifulSoup
from unittest.mock import Mock
from types import GeneratorType

from django.test import TestCase

from datagrowth.processors import ExtractProcessor
from project.mocks.data import (MOCK_HTML, MOCK_XML, MOCK_SCRAPE_DATA, MOCK_DATA_WITH_RECORDS, MOCK_JSON_DATA,
                                MOCK_DATA_WITH_KEYS)


class ExtractTextImplementation(object):

    @classmethod
    def get_html_elements(self, soup):
        return soup.find_all('a')

    @classmethod
    def get_xml_elements(self, soup):
        return soup.find_all('result')

    @classmethod
    def get_page_text(cls, soup):
        return soup.find('title').text

    @classmethod
    def get_html_link(cls, soup, el):
        return el['href']

    @classmethod
    def get_xml_link(cls, soup, el):
        return el.find('url').text


class ExtractJSONImplementation(object):

    @classmethod
    def get_nodes(cls, root):
        return root.get("records", [])

    @classmethod
    def get_dict(cls, root):
        return root.get("records")[0]

    @classmethod
    def get_keys_nodes(cls, root):
        return root.get("keys", [])

    @classmethod
    def get_json_unicode(cls, root):
        unicode = root.get("unicode", None)
        return unicode[0] if unicode else None

    @classmethod
    def get_json_id(cls, node):
        return node.get("id", None)


class TestExtractProcessor(TestCase):

    def get_html_processor(self, callables=False):
        at = "soup.find_all('a')" if not callables else ExtractTextImplementation.get_html_elements
        link = "el['href']" if not callables else ExtractTextImplementation.get_html_link
        page = "soup.find('title').text" if not callables else ExtractTextImplementation.get_page_text
        objective = {
            "@": at,
            "text": "el.text",
            "link": link,
            "#page": page,
        }
        return ExtractProcessor(config={"objective": objective})

    def get_xml_processor(self, callables=False):
        at = "soup.find_all('result')" if not callables else ExtractTextImplementation.get_xml_elements
        link = "el.find('url').text" if not callables else ExtractTextImplementation.get_xml_link
        page = "soup.find('title').text" if not callables else ExtractTextImplementation.get_page_text
        objective = {
            "@": at,
            "text": "el.find('label').text",
            "link": link,
            "#page": page,
        }
        return ExtractProcessor(config={"objective": objective})

    def get_json_processor(self, callables=False, object_values=False, from_dict=False):
        if not object_values and not from_dict:
            at = "$.records" if not callables else ExtractJSONImplementation.get_nodes
        elif from_dict:
            at = "$.records.0" if not callables else ExtractJSONImplementation.get_dict
        elif object_values:
            at = "$.keys" if not callables else ExtractJSONImplementation.get_keys_nodes
        unicode = "$.unicode.0" if not callables else ExtractJSONImplementation.get_json_unicode
        id = "$.id" if not callables else ExtractJSONImplementation.get_json_id
        objective = {
            "@": at,
            "#unicode": unicode,
            "#goal": "$.dict.dict.test",
            "id": id,
            "record": "$.record"
        }
        return ExtractProcessor(config={"objective": objective, "extract_from_object_values": object_values})

    def setUp(self):
        super(TestCase, self).setUp()

        self.content_types = ["text/html", "text/xml", "application/xml", "application/json",
                              "application/vnd.api+json", "application/quantum"]

        self.soup = BeautifulSoup(MOCK_HTML, "html5lib")
        self.xml = BeautifulSoup(MOCK_XML, "lxml")
        self.json_records = MOCK_DATA_WITH_RECORDS
        self.json_dict = MOCK_DATA_WITH_KEYS

        self.test_resources_data = [self.soup, self.xml, self.xml, self.json_records, self.json_records, None]
        self.test_resources_extractions = [
            MOCK_SCRAPE_DATA, MOCK_SCRAPE_DATA, MOCK_SCRAPE_DATA, MOCK_JSON_DATA, MOCK_JSON_DATA, None
        ]
        self.test_resources = [
            (Mock(content=(content_type, data)), processor,)
            for content_type, data, processor in zip(
                self.content_types,
                self.test_resources_data,
                [
                    self.get_html_processor(),
                    self.get_xml_processor(callables=True),
                    self.get_xml_processor(callables=True),
                    self.get_json_processor(),
                    self.get_json_processor(),
                    self.get_html_processor()
                ]
            )
        ]

    def test_init_and_load_objective(self):
        html_prc_eval = self.get_html_processor()
        self.assertEqual(html_prc_eval._at, "soup.find_all('a')")
        self.assertEqual(html_prc_eval._context, {"page": "soup.find('title').text"})
        self.assertEqual(html_prc_eval._objective, {"text": "el.text", "link": "el['href']"})
        html_prc = self.get_html_processor(callables=True)
        self.assertEqual(html_prc._at, ExtractTextImplementation.get_html_elements)
        self.assertEqual(html_prc._context, {"page": ExtractTextImplementation.get_page_text})
        self.assertEqual(html_prc._objective, {"text": "el.text", "link": ExtractTextImplementation.get_html_link})

    def test_extract(self):
        html_prc = self.get_html_processor(callables=True)
        html_prc.text_html = Mock()
        html_prc.text_xml = Mock()
        html_prc.application_json = Mock()
        for content_type in self.content_types:
            try:
                html_prc.extract(content_type, {"test": "test"})
            except TypeError:
                self.assertEqual(
                    content_type,
                    "application/quantum", "{} does not exist as a method on ExtractProcessor.".format(content_type)
                )
        self.assertEqual(html_prc.text_html.call_count, 1)
        self.assertEqual(html_prc.text_xml.call_count, 1)
        self.assertEqual(html_prc.application_json.call_count, 2)
        self.assertEqual(html_prc.extract(None, None), [])

    def test_extract_from_resource(self):
        data = []
        try:
            for test_resource in self.test_resources:
                resource, processor = test_resource
                data.append(processor.extract_from_resource(resource))
            self.fail("Wrong content_type did not raise exception")
        except TypeError:
            pass
        for test_result, expected_data in zip(data, self.test_resources_extractions):
            self.assertIsInstance(test_result, GeneratorType)
            self.assertEqual(list(test_result), expected_data)

    def test_pass_resource_through(self):
        for test_resource, expected_data in zip(self.test_resources, self.test_resources_data):
            resource, processor = test_resource
            data = processor.pass_resource_through(resource)
            self.assertNotIsInstance(data, GeneratorType)
            self.assertIs(data, expected_data)

    def test_html_text(self):
        html_prc_eval = self.get_html_processor()
        rsl = html_prc_eval.text_html(self.soup)
        self.assertEqual(list(rsl), MOCK_SCRAPE_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
        html_prc = self.get_html_processor(callables=True)
        rsl = html_prc.text_html(self.soup)
        self.assertEqual(list(rsl), MOCK_SCRAPE_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")

    def test_xml_text(self):
        xml_prc_eval = self.get_xml_processor()
        rsl = xml_prc_eval.text_xml(self.xml)
        self.assertEqual(list(rsl), MOCK_SCRAPE_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
        xml_prc = self.get_xml_processor(callables=True)
        rsl = xml_prc.text_xml(self.xml)
        self.assertEqual(list(rsl), MOCK_SCRAPE_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")

    def test_application_json_records(self):
        json_prc_eval = self.get_json_processor()
        rsl = json_prc_eval.application_json(self.json_records)
        self.assertEqual(list(rsl), MOCK_JSON_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
        json_prc = self.get_json_processor(callables=True)
        rsl = json_prc.application_json(self.json_records)
        self.assertEqual(list(rsl), MOCK_JSON_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")

    def test_application_json_object_values(self):
        keys_processor_eval = self.get_json_processor(object_values=True)
        rsl = keys_processor_eval.application_json(self.json_dict)
        self.assertEqual(list(rsl), MOCK_JSON_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
        keys_processor = self.get_json_processor(callables=True, object_values=True)
        rsl = keys_processor.application_json(self.json_dict)
        self.assertEqual(list(rsl), MOCK_JSON_DATA)
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")

    def test_application_json_dict(self):
        keys_processor_eval = self.get_json_processor(from_dict=True)
        rsl = keys_processor_eval.application_json(self.json_records)
        self.assertEqual(list(rsl), [MOCK_JSON_DATA[0]])
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
        keys_processor = self.get_json_processor(callables=True, from_dict=True)
        rsl = keys_processor.application_json(self.json_records)
        self.assertEqual(list(rsl), [MOCK_JSON_DATA[0]])
        self.assertIsInstance(rsl, GeneratorType, "Extractors are expected to return generators.")
