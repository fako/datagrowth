import logging
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
DATAGROWTH_BIN_DIR = getattr(
    settings, "DATAGROWTH_BIN_DIR",
    os.path.join(settings.BASE_DIR, "datagrowth", "resources", "shell", "bin")
)

DATAGROWTH_REQUESTS_PROXIES = getattr(settings, "DATAGROWTH_REQUESTS_PROXIES", None)
DATAGROWTH_REQUESTS_VERIFY = getattr(settings, "DATAGROWTH_REQUESTS_VERIFY", True)

DATAGROWTH_MAX_BATCH_SIZE = getattr(settings, "DATAGROWTH_MAX_BATCH_SIZE", 100)

DATAGROWTH_KALDI_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_BASE_PATH", "")
DATAGROWTH_KALDI_ASPIRE_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_ASPIRE_BASE_PATH", "")
DATAGROWTH_KALDI_NL_BASE_PATH = getattr(settings, "DATAGROWTH_KALDI_NL_BASE_PATH", "")


######################################
# DEFAULT CONFIGURATION SETTINGS
######################################


DATAGROWTH_DEFAULT_CONFIGURATION = getattr(settings, "DATAGROWTH_DEFAULT_CONFIGURATION", {
    # Global configurations that control multiple classes
    "global_asynchronous": True,  # by default offload to celery where possible
    "global_batch_size": 100,
    "global_sample_size": 0,
    "global_datatypes_app_label": None,
    "global_datatype_models": {
        "document": "Document",
        "collection": "Collection",
        "dataset_version": "DatasetVersion",
        "process_result": "ProcessResult",
        "batch": "Batch"
    },
    # Legacy global pipeline configuration, use datatype configurations instead
    "global_pipeline_app_label": None,
    "global_pipeline_models": {
        "document": "Document",
        "process_result": "ProcessResult",
        "batch": "Batch"
    },
    # Resources specific "global" configurations
    "global_user_agent": "DataGrowth (v{})".format(DATAGROWTH_VERSION),
    "global_purge_after": {},
    "global_purge_immediately": False,  # by default keep resources around
    "global_cache_only": False,
    "global_resource_exception_log_level": logging.DEBUG,
    "global_resource_exception_reraise": False,

    "http_resource_continuation_limit": 1,
    "http_resource_interval_duration": 0,  # NB: milliseconds!
    "http_resource_concat_args_size": 0,
    "http_resource_concat_args_symbol": "|",
    # TODO: these two configurations should be http_resource, not global
    "global_allow_redirects": True,
    "global_backoff_delays": [2, 4, 8, 16],

    "shell_resource_interval_duration": 0,  # NB: milliseconds!

    "wikipedia_wiki_country": "en",
    "wikipedia_wiki_query_param": "titles",
    "wikipedia_wiki_full_extracts": False,
    "wikipedia_wiki_domain": "en.wikipedia.org",
    "wikipedia_wiki_show_categories": "!hidden",

    "google_api_key": getattr(settings, 'GOOGLE_API_KEY', ''),
    "google_cx": getattr(settings, 'GOOGLE_CX', ''),

    "growth_processor_extractor": "ExtractProcessor.extract_from_resource",
    "growth_processor_depends_on": None,
    "growth_processor_to_property": None,
    "growth_processor_apply_resource_to": [],

    "rank_processor_batch_size": 1000,
    "rank_processor_result_size": 20,

    "extract_processor_extract_from_object_values": False,
    "transform_processor_extract_from_object_values": False,

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
