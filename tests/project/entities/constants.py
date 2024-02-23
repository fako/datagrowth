from collections import OrderedDict


class Entities(object):
    PAPER = "paper"
    AUTHOR = "author"
    JOURNAL = "journal"


class EntityStates(object):
    OPEN = "open"
    RESTRICTED = "restricted"
    CLOSED = "closed"
    DELETED = "deleted"


PAPER_DEFAULTS = {
    "id": None,
    "state": EntityStates.OPEN,
    "doi": None,
    "title": None,
    "abstract": None,
    "authors": [],
    "url": None,
    "published_at": None,
    "modified_at": None,
}

AUTHOR_DEFAULTS = {
    "id": None,
    "state": EntityStates.OPEN,
    "isni": None,
    "first_name": None,
    "last_name": None,
    "email": None,
}

JOURNAL_DEFAULTS = {
    "id": None,
    "state": EntityStates.OPEN,
    "title": None,
    "description": None,
    "website": None,
    "papers": [],
    "authors": [],
}


SEED_DEFAULTS = {
    Entities.PAPER: PAPER_DEFAULTS,
    Entities.AUTHOR: AUTHOR_DEFAULTS,
    Entities.JOURNAL: JOURNAL_DEFAULTS
}

SEED_SEQUENCE_PROPERTIES = {
    "id": "{ix}",
    "title": "Title for {ix}",
    "abstract": "Abstract for {ix}",
    "doi": "https://doi.org/10.{ix}",
    "isni": "https://isni.org/{ix}"
}

SEED_CYCLE_PROPERTIES = OrderedDict([
    ("first_name", ["Marie", "Isaac", "Daniel", "Niels", "Albert"],),
    ("last_name", ["Curie", "Newton", "Kahneman", "Bohr"],),
    ("description", ["Science is da bomb!", "Nature is where it's at!", "I'm boring."],),
    ("website", ["https://science.org", "https://nature.org", "https://academic.oup.com"],),
    ("url", ["https://science.org/{ix}.pdf", "https://nature.org/{ix}.pdf", "https://academic.oup.com/{ix}.pdf"],),
    ("email", [
        "{first_name}.{last_name}@science.org",
        "{first_name}.{last_name}@nature.org",
        "{first_name}.{last_name}@academic.oup.com",
    ],),
])
