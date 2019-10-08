import os
from tqdm import tqdm

from django.core.serializers import serialize, deserialize

from datagrowth import settings as datagrowth_settings
from datagrowth.utils.iterators import ibatch


def get_model_path(app_label, model_type=""):
    """
    Returns a path to a directory inside the global data directory specified by ``DATAGROWTH_DATA_DIR``.
    The idea is to store computer models inside this directory.
    The path will contain the app_label to make sure that related models are stored together.
    It optionally also includes a subdirectory for the model type in order to separate different computer models.

    :param app_label: (str) the app label that is related to the computer model you're getting a path for
    :param model_type: (str) an optional model type that can further group models within apps
    :return: path to models directory without a trailing slash
    """
    return os.path.join(datagrowth_settings.DATAGROWTH_DATA_DIR, app_label, model_type).rstrip(os.sep)


def get_media_path(app_label, media_type="", absolute=True):
    """
    Returns a directory path for a particular app to store media in.
    Optionally this path can include a media type to further separate media files in subdirectories.
    By default the path is absolute and inside the ``DATAGROWTH_MEDIA_ROOT``,
    but you can also return a path relative to the media root directory.

    :param app_label: (str) the app label that you're getting a media path for
    :param media_type: (str) an optional media type that can further group media within apps
    :param absolute: (bool) whether to return an absolute or relative path
    :return: path to media directory without a trailing slash
    """
    if absolute:
        return os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, app_label, media_type).rstrip(os.sep)
    else:
        return os.path.join(app_label, media_type).rstrip(os.sep)


def get_dumps_path(model):
    return os.path.join(datagrowth_settings.DATAGROWTH_DATA_DIR, model._meta.app_label, "dumps", model.get_name())


def queryset_to_disk(queryset, dump_file, batch_size=100, progress_bar=True):
    count = queryset.all().count()
    batch_iterator = ibatch(queryset.iterator(), batch_size=batch_size, progress_bar=progress_bar, total=count)
    for batch in batch_iterator:
        batch_data = serialize("json", batch, use_natural_foreign_keys=True)
        dump_file.writelines([batch_data + "\n"])


def object_to_disk(object, dump_file):
    batch_data = serialize("json", [object], use_natural_foreign_keys=True)
    dump_file.write(batch_data + "\n")


def objects_from_disk(dump_file, progress_bar=True):
    batch_count = 0
    for _ in dump_file.readlines():
        batch_count += 1
    dump_file.seek(0)
    for line in tqdm(dump_file, total=batch_count, disable=not progress_bar):
        yield [wrapper.object for wrapper in deserialize("json", line)]
