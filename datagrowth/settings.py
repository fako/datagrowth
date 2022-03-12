import os

from django.conf import settings

from datagrowth.version import VERSION


######################################
# PLAIN SETTINGS
######################################


DATAGROWTH_VERSION = VERSION
DATAGROWTH_API_VERSION = getattr(settings, "DATAGROWTH_API_VERSION", 1)

DATAGROWTH_DATETIME_FORMAT = getattr(settings, "DATAGROWTH_DATETIME_FORMAT", "%Y%m%d%H%M%S%f")

DATAGROWTH_DATA_DIR = getattr(settings, "DATAGROWTH_DATA_DIR", os.path.join(settings.BASE_DIR, "data"))
DATAGROWTH_MEDIA_ROOT = getattr(settings, "DATAGROWTH_MEDIA_ROOT", settings.MEDIA_ROOT)
DATAGROWTH_BIN_DIR = getattr(settings, "DATAGROWTH_BIN_DIR",
    os.path.join(settings.BASE_DIR, "datagrowth", "resources", "shell", "bin")
)

DATAGROWTH_REQUESTS_PROXIES = getattr(settings, "DATAGROWTH_REQUESTS_PROXIES", None)
DATAGROWTH_REQUESTS_VERIFY = getattr(settings, "DATAGROWTH_REQUESTS_VERIFY", True)

DATAGROWTH_MAX_BATCH_SIZE = getattr(settings, "DATAGROWTH_MAX_BATCH_SIZE", 500)

DATAGROWTH_KALDI_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_BASE_PATH", "")
DATAGROWTH_KALDI_ASPIRE_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_ASPIRE_BASE_PATH", "")
DATAGROWTH_KALDI_NL_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_NL_BASE_PATH", "")


######################################
# DEFAULT CONFIGURATION SETTINGS
######################################


DATAGROWTH_DEFAULT_CONFIGURATION = getattr(settings, "DATAGROWTH_DEFAULT_CONFIGURATION", {
    "global_asynchronous": True,  # by default offload to celery where possible
    "global_async": True,  # legacy "asynchronous" configuration for Python <= 3.6
    "global_user_agent": "DataGrowth (v{})".format(DATAGROWTH_VERSION),
    "global_purge_after": {},
    "global_purge_immediately": False,  # by default keep resources around
    "global_sample_size": 0,
    "global_cache_only": False,

    "http_resource_continuation_limit": 1,
    "http_resource_interval_duration": 0,  # NB: milliseconds!
    "http_resource_concat_args_size": 0,
    "http_resource_concat_args_symbol": "|",
    "global_backoff_delays": [2, 4, 8, 16],

    "shell_resource_interval_duration": 0,  # NB: milliseconds!

    "wikipedia_wiki_country": "en",
    "wikipedia_wiki_query_param": "titles",
    "wikipedia_wiki_full_extracts": False,
    "wikipedia_wiki_domain": "en.wikipedia.org",
    "wikipedia_wiki_show_categories": "!hidden",

    "google_api_key": getattr(settings, 'GOOGLE_API_KEY', ''),
    "google_cx": getattr(settings, 'GOOGLE_CX', ''),

    "indico_api_key": getattr(settings, 'INDICO_API_KEY', ''),
    "wizenoze_api_key": getattr(settings, 'WIZENOZE_API_KEY', ''),

    "rank_processor_batch_size": 1000,
    "rank_processor_result_size": 20,

    "extract_processor_extract_from_object_values": False,

    "micro_service_connections": {
        "image_recognition": {
            "protocol": "http",
            "host": "localhost:2000",
            "path": "/predict/"
        },
        "clothing_type_recognition": {
            "protocol": "http",
            "host": "localhost:2001",
            "path": "/predict/"
        }
    }
})


DATAGROWTH_MOCK_CONFIGURATION = {
    # HttpResource (processor)
    "mock_processor_include_odd": False,
    "mock_processor_include_even": False,
    # micro services
    "micro_service_connections": {
        "mock_service": {
            "protocol": "http",
            "host": "localhost:2000",
            "path": "/service/"
        }
    }
}
