from urllib.parse import urlparse, parse_qs
from datagrowth.resources import TestClientResource


class EntityResource(TestClientResource):

    PARAMETERS = {
        "size": 20,
        "page_size": 10
    }

    def next_parameters(self):
        content_type, data = self.content
        if not data or not (next_url := data["next"]):
            return {}
        next_link = urlparse(next_url)
        params = parse_qs(next_link.query)
        return {
            "page": params["page"]
        }

    class Meta:
        abstract = True


class EntityListResource(EntityResource):
    test_view_name = "entities"


class EntityIdListResource(EntityResource):
    test_view_name = "entity-ids"


class EntityDetailResource(EntityResource):
    test_view_name = "entity-detail"
