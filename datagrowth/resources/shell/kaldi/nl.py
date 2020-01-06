import os
import hashlib
import re

from django.conf import settings

from datagrowth import settings as datagrowth_settings
from datagrowth.resources.shell import ShellResource


class KaldiNLResource(ShellResource):
    """
    Usage:

    resource = KaldiNLResource().run(<file-path>)
    content_type, transcript = resource.content
    """

    CMD_TEMPLATE = [
        "bash",
        "kaldi_nl.bash",  # NB: copy this file into the Kaldi NL directory
        "{}"
    ]
    FLAGS = {}
    VARIABLES = {
        "KALDI_ROOT": datagrowth_settings.DATAGROWTH_KALDI_BASE_PATH,
        "BASE_DIR": settings.BASE_DIR,
        "OUTPUT_PATH": None  # gets set at runtime
    }
    CONTENT_TYPE = "text/plain"
    DIRECTORY_SETTING = "DATAGROWTH_KALDI_NL_BASE_PATH"

    def environment(self, *args, **kwargs):
        env = super().environment()
        hsh = hashlib.sha1()
        vars = self.variables(*args)
        hsh.update(" ".join(vars["input"]).encode("utf-8"))
        env["OUTPUT_PATH"] = os.path.join("output", hsh.hexdigest())
        return env

    def clean_stdout(self, stdout):
        stdout = super().clean_stdout(stdout)
        return "".join((
            output
            for output in stdout.split("\r") if
            not output.startswith("Rescoring..") and
            not output.startswith("[") and
            not output.startswith("NNet3 Decoding")
        ))

    def transform(self, stdout):
        if not stdout:
            return
        is_transcript = False
        out = []
        for line in stdout.split("\n"):
            if line == "=== TRANSCRIPTION ===":
                is_transcript = True
            elif line == "=== END TRANSCRIPTION ===":
                is_transcript = False
            elif is_transcript:
                out.append(line)
        return re.sub(" \(.+\)$", "", "\n".join(out), flags=re.MULTILINE)

    class Meta:
        abstract = True
