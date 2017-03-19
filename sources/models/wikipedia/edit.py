from core.exceptions import DSHttpError400NoToken

from sources.models.wikipedia.query import WikipediaAPI


class WikipediaEdit(WikipediaAPI):

    URI_TEMPLATE = "https://{}.wikipedia.org/w/api.php"

    DATA = {
        'action': 'edit',
        'assert': 'user',
        'format': 'json',
        'utf8': '',
        'nocreate': 1
    }

    POST_SCHEMA = {
        "args": {
            "title": "edit arguments",
            "type": "array",
            "items": [
                {
                    "type": "string",
                    "pattern": "[a-z]{2}"
                }
            ],
            "additionalItems": False,
            "minItems": 1
        },
        "kwargs": {
            "title": "edit keyword arguments",
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                },
                "text": {
                    "type": "string",
                }
            },
            "required": ["title", "text"]
        }
    }

    def __init__(self, *args, **kwargs):
        self.token = kwargs.pop("token", None)
        super(WikipediaEdit, self).__init__(*args, **kwargs)

    def data(self, **kwargs):
        data = super(WikipediaEdit, self).data(**kwargs)
        if not self.token:
            raise DSHttpError400NoToken(
                "No edit token specified for WikipediaEdit. Use WikipediaToken to fetch one",
                resource=self
            )
        data["token"] = self.token
        return data

    def parameters(self, **kwargs):
        parameters = dict(self.PARAMETERS)
        parameters.pop("continue", None)
        return parameters

    def send(self, method, *args, **kwargs):
        args = (self.config.wiki_country,)
        return super(WikipediaEdit, self).send(method, *args, **kwargs)

    def get(self, *args, **kwargs):
        raise NotImplementedError("GET is not implemented for this resource")
