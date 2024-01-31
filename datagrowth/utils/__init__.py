from .iterators import ibatch
from .datetime import parse_datetime_string, format_datetime
from .io import get_model_path, get_media_path, get_dumps_path, object_to_disk, queryset_to_disk, objects_from_disk
from .data import reach, override_dict, is_json_mimetype
from .tasks import DatabaseConnectionResetTask


def is_hashable(obj: object) -> bool:
    try:
        hash(obj)
    except TypeError:
        return False
    else:
        return True
