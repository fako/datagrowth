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


######################################
# DEFAULT CONFIGURATION SETTINGS
######################################


DATAGROWTH_DEFAULT_CONFIGURATION = getattr(settings, "DATAGROWTH_DEFAULT_CONFIGURATION", {
    # Global configurations that control multiple classes
    "global_datetime_format": DATAGROWTH_DATETIME_FORMAT,
    "global_asynchronous": True,  # by default offload to celery where possible
    "global_batch_size": 100,
    "global_max_batch_size": DATAGROWTH_MAX_BATCH_SIZE,
    "global_sample_size": 0,
    "global_datatypes_app_label": None,
    "global_datatype_models": {
        "document": "Document",
        "collection": "Collection",
        "dataset_version": "DatasetVersion",
        "process_result": "ProcessResult",
        "batch": "Batch"
    },
    "global_data_dir": DATAGROWTH_DATA_DIR,
    # Resources specific "global" configurations
    "global_purge_after": {},
    "global_purge_immediately": False,  # by default keep resources around
    "global_cache_only": False,
    "global_resource_exception_log_level": logging.DEBUG,
    "global_resource_exception_reraise": False,
    # HttpResource configurations
    "http_resource_requests_proxies": DATAGROWTH_REQUESTS_PROXIES,
    "http_resource_requests_verify": DATAGROWTH_REQUESTS_VERIFY,
    "http_resource_user_agent": "DataGrowth (v{})".format(DATAGROWTH_VERSION),
    "http_resource_continuation_limit": 1,
    "http_resource_interval_duration": 0,  # NB: milliseconds!
    "http_resource_concat_args_size": 0,
    "http_resource_concat_args_symbol": "|",
    "http_resource_allow_redirects": True,
    "http_resource_backoff_delays": [2, 4, 8, 16],
    "http_resource_force_data_file_to_payload": False,
    # ShellResource configurations
    "shell_resource_interval_duration": 0,  # NB: milliseconds!
    "shell_resource_bin_dir": DATAGROWTH_BIN_DIR,
    # Data gathering and transformation configurations
    "growth_processor_extractor": "ExtractProcessor.extract_from_resource",
    "growth_processor_depends_on": None,
    "growth_processor_to_property": None,
    "growth_processor_apply_resource_to": [],
    "extract_processor_extract_from_object_values": False,
    "transform_processor_extract_from_object_values": False,
    # MicroserviceResource configurations
    "micro_service_connections": {},
    # Web configurations when exposing Datagrowth functionality through for instance Django
    "web_api_version": DATAGROWTH_API_VERSION,
    "web_media_root": DATAGROWTH_MEDIA_ROOT,
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
