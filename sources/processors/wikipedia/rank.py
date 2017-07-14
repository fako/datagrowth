from core.processors.rank import RankProcessor


class WikipediaRankProcessor(RankProcessor):

    def get_hook_arguments(self, individual):
        individual_argument = super(WikipediaRankProcessor, self).get_hook_arguments(individual)[0]
        wikidata_argument = individual_argument.get("wikidata", {})
        if wikidata_argument is None or isinstance(wikidata_argument, str):
            wikidata_argument = {}
        return [individual_argument, wikidata_argument]

    @staticmethod
    def revision_count(page, wikidata):
        return len(page.get("revisions", []))

    @staticmethod
    def category_count(page, wikidata):
        return len(page.get("categories", []))

    @staticmethod
    def number_of_deaths(page, wikidata):
        number_of_deaths_property = "P1120"
        return next(
            (claim["value"] for claim in wikidata.get("claims", [])
            if claim["property"] == number_of_deaths_property)
        , 0)

    @staticmethod
    def women(page, wikidata):
        sex_property = "P21"
        women_item = "Q6581072"
        return any(
            (claim for claim in wikidata.get("claims", [])
            if claim["property"] == sex_property and claim["value"] == women_item)
        )

    @staticmethod
    def breaking_news(page, wikidata):
        # Based on: https://arxiv.org/abs/1303.4702

        # Function guards
        revisions = page.get("revisions", [])
        if not len(revisions):
            return None

        # First we build "clusters" of revisions (aka edits) that happened 60 seconds from each other
        clusters = []
        revisions = iter(revisions)
        cluster_revisions = [next(revisions)]
        for revision in revisions:
            last_revision_timestamp = cluster_revisions[-1].get("timestamp")
            if revision.get("timestamp") - last_revision_timestamp > 60:
                if len(cluster_revisions) > 1:
                    clusters.append(cluster_revisions)
                cluster_revisions = [revision]
                continue
            cluster_revisions.append(revision)

        # Now we check the clusters for the breaking news quality defined as:
        # At least 5 concurrent revisions
        # At least 3 editors involved
        # One such cluster is sufficient to mark page as breaking news
        for cluster in clusters:
            if len(cluster) < 5:
                continue
            unique_editors = set([revision["userid"] for revision in cluster])
            if len(unique_editors) >= 3:
                return True

        # No breaking news clusters
        return
