import json

from datagrowth.resources.shell import ShellResource


class TikaResource(ShellResource):

    CMD_TEMPLATE = [
        "java",
        "-jar",
        "bin/tika-app-1.19.1.jar",
        "-J",
        "-t",
        "{}"
    ]
    CONTENT_TYPE = "application/json"
    DIRECTORY_SETTING = "DATAGROWTH_BIN_DIR"

    @property
    def content(self):
        content_type, raw = super().content
        if not raw:
            return content_type, raw
        data = json.loads(raw)
        return content_type, data[0]  # TODO: allow multiple document input

    class Meta:
        abstract = True
