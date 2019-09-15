from copy import copy

from datagrowth.configuration import ConfigurationProperty
from datagrowth.utils import reach
from datagrowth.processors.base import Processor
from datagrowth.exceptions import DGNoContent


class ExtractProcessor(Processor):

    config = ConfigurationProperty(
        storage_attribute="_config",
        defaults=None,  # This will now lookup defaults at package level. Use register_defaults to set defaults.
        private=["_objective"],
        namespace="extract_processor"
    )

    def __init__(self, config):
        super(ExtractProcessor, self).__init__(config)
        self._at = None
        self._context = {}
        self._objective = {}
        if "_objective" in config or "objective" in config:
            self.load_objective(self.config.objective)

    def load_objective(self, objective):
        assert isinstance(objective, dict), "An objective should be a dict."
        for key, value in objective.items():
            if key == "@":
                self._at = value
            elif key.startswith("#"):
                self._context.update({key[1:]: value})
            else:
                self._objective.update({key: value})
        assert self._objective or self._context, "No objectives loaded from objective {}".format(objective)
        if self._objective:
            assert self._at, \
                "ExtractProcessor did not load elements to start with from its objective {}. " \
                "Make sure that '@' is specified".format(objective)

    def pass_resource_through(self, resource):
        mime_type, data = resource.content
        return data

    def extract_from_resource(self, resource):
        return self.extract(*resource.content)

    def extract(self, content_type, data):
        assert self.config.objective, \
            "ExtractProcessor.extract expects an objective to extract in the configuration."
        if content_type is None:
            return []
        content_type_method = content_type.replace("/", "_")
        method = getattr(self, content_type_method, None)
        if method is not None:
            return method(data)
        else:
            raise TypeError("Extract processor does not support content_type {}".format(content_type))

    def application_json(self, data):
        context = {}
        for name, objective in self._context.items():
            context[name] = reach(objective, data)

        nodes = reach(self._at, data)
        if isinstance(nodes, dict):
            nodes = nodes.values()

        if nodes is None:
            raise DGNoContent("Found no nodes at {}".format(self._at))

        for node in nodes:
            result = copy(context)
            for name, objective in self._objective.items():
                result[name] = reach(objective, node)
            yield result

    @staticmethod
    def _eval_extraction(name, objective, soup, el=None):
        try:
            return eval(objective) if objective else None
        except Exception as exc:
            raise ValueError("Can't extract '{}'".format(name)) from exc

    def _extract_soup(self, soup):  # soup used in eval!

        context = {}
        for name, objective in self._context.items():
            context[name] = self._eval_extraction(name, objective, soup)

        at = elements = self._eval_extraction("@", self._at, soup)
        if not isinstance(at, list):
            elements = [at]

        for el in elements:  # el used in eval!
            result = copy(context)
            for name, objective in self._objective.items():
                if not objective:
                    continue
                result[name] = self._eval_extraction(name, objective, soup, el)
            yield result

    def text_html(self, soup):
        for result in self._extract_soup(soup):
            yield result

    def text_xml(self, soup):
        for result in self._extract_soup(soup):
            yield result
