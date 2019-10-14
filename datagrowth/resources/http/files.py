import os
from io import BytesIO
import hashlib
from PIL import Image
from urlobject import URLObject
from datetime import datetime
import requests

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files import File
from django.core.files.images import ImageFile

from datagrowth import settings as datagrowth_settings
from datagrowth.resources.http.generic import URLResource


class HttpFileResource(URLResource):
    """
    Sometimes you want to download a file instead of storing the content in the database.
    For this use case the ``HttpFileResource`` is very suitable.
    Just pass the URL as a first argument to ``get`` and the URL will be downloaded as a file,
    storing it in your ``MEDIA_ROOT``.

    The file path of the downloaded file will get stored in the ``body`` field.
    This path will be relative to the ``MEDIA_ROOT``.
    The path will include a downloads folder and a subfolder that is the ``app_name`` of the concrete class.
    Under that directory there are many possible subdirectories in the form of "x/yz/".
    Where x, y and z will be hexidecimal characters.
    Creating these subdirectories is necessary to prevent huge download directories, that would hamper performance.

    Only full URL's with protocol will get downloaded.
    Any URL's without a protocol will get stored as a failure with a 404 (Not Found) error code.
    Please note that with this class it is not possible to adjust the parameters through the ``parameters`` method,
    because it is assumed that all parameters are part of the URL given to ``get``.
    """

    GET_SCHEMA = {
        "args": {
            "type": "array",
            "items": [
                {
                    "type": "string",
                    "pattern": "^http"
                }
            ],
            "minItems": 1,
            "additionalItems": False
        }
    }

    def _send(self):
        if self.request["cancel"]:
            return
        super()._send()

    def _create_request(self, method, *args, **kwargs):
        cancel_request = False
        try:
            self._validate_input("get", *args, **kwargs)
        except ValidationError as exc:
            url = args[0] if len(args) else None
            if url is None or url.startswith("http"):
                raise exc
            # Wrong protocol given, like: x-raw-image://
            self.set_error(404)
            cancel_request = True
        headers = requests.utils.default_headers()
        headers["User-Agent"] = "{}; {}".format(self.config.user_agent, headers["User-Agent"])
        headers.update(self.headers())
        return self.validate_request({
            "args": args,
            "kwargs": kwargs,
            "method": "get",
            "url": self._create_url(*args),
            "headers": dict(headers),
            "data": None,
            "cancel": cancel_request
        }, validate_input=False)

    def _get_file_class(self):
        return File

    @staticmethod
    def get_file_name(original, now):
        """
        Override this method to change the file naming convention.
        By default it will take the filename from the URL
        and prefix it with a datetime string of the date and time at downloading.

        :param original: (str) the URL file name
        :param now: (datetime) a datetime object to use as prefix input
        :return:
        """
        return "{}.{}".format(
            now.strftime(datagrowth_settings.DATAGROWTH_DATETIME_FORMAT),
            original
        )

    def _get_file_info(self, url):
        # Getting the file name and extension from url
        path = str(URLObject(url).path)
        tail, head = os.path.split(path)
        if not head:
            head = "index.html"
        name, extension = os.path.splitext(head)
        if not extension:
            extension = ".html"
        now = datetime.utcnow()
        file_name = self.get_file_name(name, now)
        # Hashing the file name
        hasher = hashlib.md5()
        hasher.update(file_name.encode('utf-8'))
        file_hash = hasher.hexdigest()
        # Constructing file path
        file_path = os.path.join(
            datagrowth_settings.DATAGROWTH_MEDIA_ROOT,
            self._meta.app_label,
            "downloads",
            file_hash[0], file_hash[1:3]  # this prevents huge (problematic) directory listings
        )
        return file_path, file_name, extension

    def _save_file(self, url, content):
        file_path, file_name, extension = self._get_file_info(url)
        if len(file_name) > 150:
            file_name = file_name[:150]
        file_name += extension
        if len(file_name) > 155:
            file_name = file_name[:155]
        FileClass = self._get_file_class()
        file = FileClass(BytesIO(content))
        file_name = default_storage.save(os.path.join(file_path, file_name), file)
        return file_name

    def _update_from_results(self, response):
        file_name = self._save_file(self.request["url"], response.content)
        self.head = dict(response.headers)
        self.status = response.status_code
        self.body = file_name.replace(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, "").lstrip(os.sep)

    def transform(self, file):
        """
        By default the ``content`` property will return the file wrapped in a Django ``File`` class.
        It may be convenient to wrap it in some other way.
        Override this method and return the file in a different format to change the content return value.

        :param file: (File) the file read from storage
        :return: (any) file in correct format
        """
        return file

    @property
    def content(self):
        """
        Opens the file stored at the file path in ``body`` and returns that file together with the content type.

        :return: content_type, file
        """
        if self.success:
            content_type = self.head.get("content-type", "unknown/unknown").split(';')[0]
            file_path = os.path.join(default_storage.location, self.body)
            file = default_storage.open(file_path)
            try:
                return content_type, self.transform(file)
            except IOError:
                return None, None
        return None, None

    def post(self, *args, **kwargs):
        raise NotImplementedError("You can't download a file over POST")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = kwargs.get("timeout", 4)

    class Meta:
        abstract = True


class HttpImageResource(HttpFileResource):
    """
    This class acts like the HttpFileResource with the only difference that it will return content as Pillow images.
    """

    def _get_file_class(self):
        return ImageFile

    def transform(self, file):
        return Image.open(file)

    class Meta:
        abstract = True


def file_resource_delete_handler(sender, instance, **kwargs):
    """
    A Django signal handler that can be bound to a ``post_delete`` signal
    to free disk space when file resources get deleted.

    :param sender: receives the class that is sending the signal
    :param instance: the object under deletion
    :param kwargs: ignored, for compatibility only
    """
    if instance.body and default_storage.exists(instance.body):
        default_storage.delete(instance.body)
