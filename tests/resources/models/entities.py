from urllib.parse import urlparse, parse_qs
from datagrowth.resources import TestClientResource


class EntityListResource(TestClientResource):

    test_view_name = "entities"

    PARAMETERS = {
        "size": 20,
        "page_size": 10
    }

    def next_parameters(self):
        content_type, data = self.content
        if not data or not (next_url := data.get("next")):
            return {}
        next_link = urlparse(next_url)
        params = parse_qs(next_link.query)
        return {
            "page": params["page"]
        }


class EntityIdListResource(TestClientResource):

    PARAMETERS = {
        "size": 10,
        "page_size": 20
    }

    test_view_name = "entity-ids"


class EntityDetailResource(TestClientResource):
    test_view_name = "entity-detail"
