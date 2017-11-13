from collections import OrderedDict

from core.models.organisms import Community, Collective, Individual
from core.utils.helpers import cross_combine


class CrossCombineTermSearchCommunity(Community):

    COMMUNITY_SPIRIT = OrderedDict([
        ("search", {
            "process": "HttpResourceProcessor.fetch_mass",
            "input": None,
            "contribute": "Append:ExtractProcessor.extract_from_resource",
            "output": "Collective#url",
            "config": {
                "_args": ["$.query", "$.quantity"],
                "_kwargs": {},
                "_resource": "GoogleText",
                "_objective": {
                    "@": "$.items",
                    "#term": "$.queries.request.0.searchTerms",
                    "title": "$.title",
                    "url": "$.link"
                },
                "_continuation_limit": 10
            },
            "schema": {},
            "errors": {},
        }),
        ("download", {
            "process": "HttpResourceProcessor.fetch_mass",
            "input": "@search",
            "contribute": "Update:ExtractProcessor.extract_from_resource",
            "output": "@search",
            "config": {
                "_args": ["$.url"],
                "_kwargs": {},
                "_resource": "WebTextResource",
                "_objective": {  # objective uses properties added to the soup by WebTextResource
                    "#url": "soup.source",
                    "#paragraph_groups": "soup.paragraph_groups"
                },
                "_update_key": "url"
            },
            "schema": {},
            "errors": {},
        })
    ])

    COMMUNITY_BODY = []
    SAMPLE_SIZE = 10

    def initial_input(self, *args):
        combinations = cross_combine(args[0], args[1])
        collective = Collective.objects.create(community=self, schema={})
        for terms in combinations:
            Individual.objects.create(
                community=self,
                collective=collective,
                properties={
                    "terms": "+".join(terms),
                    "query": " AND ".join(
                        ['"{}"'.format(term) for term in terms]
                    ),
                    "quantity": 10
                }
            )
        return collective

    def set_kernel(self):
        self.kernel = self.current_growth.output

    class Meta:
        verbose_name = "Cross combine search term community"
        verbose_name_plural = "Cross combine search term communities"
