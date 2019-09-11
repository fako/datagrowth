from django.apps import AppConfig

from datagrowth.configuration import register_defaults


class ResourcesConfig(AppConfig):
    name = 'resources'

    def ready(self):
        register_defaults("global", {
            "user_agent": "DataGrowth (test)",
            "source_language": "en"
        })
        register_defaults("mock", {"secret": "oehhh"})
