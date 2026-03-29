from django.apps import AppConfig

from datagrowth.configuration import register_defaults


class ResourcesConfig(AppConfig):
    name = 'resources'

    def ready(self):
        register_defaults("global", {
            "source_language": "en"
        })
        register_defaults("http_resource", {
            "user_agent": "DataGrowth (test)"
        })
        register_defaults("mock", {"secret": "oehhh"})
        register_defaults("micro_service", {
            "connections": {
                "service_mock": {
                    "protocol": "http",
                    "host": "localhost:8000",
                    "path": "/service"
                }
            }
        })
