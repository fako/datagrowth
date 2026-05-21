from django.test import TestCase
from datagrowth.resources.testing import ResourceFixturesMixin

from vendors.models import LegacyTikaPdfResource


class TestHttpTikaResource(ResourceFixturesMixin, TestCase):

    resource_fixtures = ["apache-resources.json"]

    def test_extract_with_semantics(self) -> None:
        # Make the structure Tika call
        structure = LegacyTikaPdfResource()
        structure = structure.extract("put", document="file://media/test.pdf")
        self.assertEqual(structure.id, 1)
        # Make the semantics Tika call
        semantic_request = structure.create_next_request()
        semantics = LegacyTikaPdfResource(request=semantic_request)
        semantics = semantics.extract("put")
        self.assertEqual(semantics.id, 2)
        # Test alternative content
        structure_content = structure.get_main_content()
        assert structure_content
        semantics.inject_alternative_content("Y-TIKA:content", structure_content["X-TIKA:content"])
        semantics.refresh_from_db()
        semantics_content = semantics.get_main_content()
        assert semantics_content
        self.assertEqual(semantics_content["Y-TIKA:content"], structure_content["X-TIKA:content"])
        self.assertNotEqual(semantics_content["X-TIKA:content"], structure_content["X-TIKA:content"])
