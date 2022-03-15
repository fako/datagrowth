from copy import copy

from datagrowth.configuration import ConfigurationProperty
from datagrowth.utils import reach, is_json_mimetype
from datagrowth.processors.base import Processor
from datagrowth.exceptions import DGNoContent


class ExtractProcessor(Processor):
    """
    The ``ExtractProcessor`` takes an objective through its configuration.
    Using this objective it will extract a list of objects from the input data possibly transforming it.

    Objectives are dictionaries that require at least an "@" key and one other item.
    Values in this dictionary can be one of the following:

     * A JSON path as described by the reach function (for JSON extraction)
     * A string containing BeautifulSoup expressions using the "soup" and "el" variables (for HTML/XML extraction, not recommended)
     * A processor name and method name (like: Processor.method) that take a soup and el argument (for HTML/XML extraction, recommended)

    These values will be called/parsed to extract data from the input data.
    The extracted data gets stored under the keys.

    The special "@" key indicates where extraction should start and its value should result in a list.
    By default objective values get evaluated against elements in the list retrieved from the '@' value.
    Objective items who's keys start with "#" will get evaluated against the entire input.

    The output of the ``ExtractProcessor`` will typically consist of a list of objects.
    Each object shares the same keys as the objective except the "@" key.
    Any keys in the objective that start with "#" will have the same value for all extracted objects,
    but the "#" will get stripped from the object keys.
    """

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
        """
        Normally an objective is passed to the ``ExtractProcessor`` through its configuration.
        Use this method to load an objective after the ``ExtractProcessor`` got initialized.

        :param objective: (dict) the objective to use for extraction
        :return: None
        """
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
        """
        Sometimes you want to retrieve data as-is without filtering and/or transforming.
        This method is a convenience method to do just that for any ``Resource``.
        It's interface is similar to ``extract_from_resource`` in that you can just pass it a ``Resource``
        and it will return the data from that ``Resource``.

        :param resource: (Resource) any resource
        :return: (mixed) the data returned by the resource
        """
        mime_type, data = resource.content
        return data

    def extract_from_resource(self, resource):
        """
        This is the most common way to extract data with this class.
        It takes a ``Resource`` (which is a source of data) and tries to extract from it immediately.

        :param resource: (Resource) any resource
        :return: (list) extracted objects from the Resource data
        """
        return self.extract(*resource.content)

    def extract(self, content_type, data):
        """
        Call this method to start extracting from the input data based on the objective.

        If your content_type is not supported by the extractor you could inherit from this class
        and write your own method.
        A content type of application/pdf would try to call an ``application_pdf`` method on this class
        passing it the data as an argument.
        The objective will be available as ``self.objective`` on the instance.

        :param content_type: (content type) The content type of the input data
        :param data: (varies) The input data to extract from
        :return: (list) extracted objects
        """
        assert self.config.objective, \
            "ExtractProcessor.extract expects an objective to extract in the configuration."
        if content_type is None:
            return []
        if is_json_mimetype(content_type):
            content_type = "application/json"
        content_type_method = content_type.replace("/", "_")
        method = getattr(self, content_type_method, None)
        if method is not None:
            return method(data)
        else:
            raise TypeError("Extract processor does not support content_type {}".format(content_type))

    def application_json(self, data):
        context = {}
        for name, objective in self._context.items():
            context[name] = reach(objective, data) if not callable(objective) else objective(data)

        nodes = reach(self._at, data) if not callable(self._at) else self._at(data)
        if isinstance(nodes, dict) and self.config.extract_from_object_values:
            nodes = nodes.values()
        elif nodes is None:
            raise DGNoContent("Found no nodes at {}".format(self._at))
        elif not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            result = copy(context)
            for name, objective in self._objective.items():
                result[name] = reach(objective, node) if not callable(objective) else objective(node)
            yield result

    @staticmethod
    def _eval_extraction(name, objective, soup, el=None):
        if callable(objective):
            return objective(soup) if el is None else objective(soup, el)
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

    def application_xml(self, soup):
        for result in self._extract_soup(soup):
            yield result
