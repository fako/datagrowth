from django.conf import settings

from datagrowth import settings as datagrowth_settings
from datagrowth.resources.shell import ShellResource


class KaldiAspireResource(ShellResource):
    """
    Usage:

    resource = KaldiAspireResource().run(<file-path>)
    content_type, transcript = resource.content
    """

    CMD_TEMPLATE = [
        "bash",
        "kaldi_en.bash",  # NB: copy this file into the Kaldi Aspire directory
        "{}"
    ]
    FLAGS = {}
    VARIABLES = {
        "KALDI_ROOT": datagrowth_settings.DATAGROWTH_KALDI_BASE_PATH,
        "BASE_DIR": settings.BASE_DIR
    }
    CONTENT_TYPE = "text/plain"
    DIRECTORY_SETTING = "DATAGROWTH_KALDI_ASPIRE_BASE_PATH"

    def _update_from_results(self, results):
        super()._update_from_results(results)
        if self.status == 0:  # no error code from command, so stderr contains the transcript
            self.stdout = self.stderr
            self.stderr = ""

    def transform(self, stdout):
        if not stdout:
            return
        is_transcript = False
        transcript_marker = "utterance-id1 "
        out = []
        for line in stdout.split("\n"):
            if line.startswith("utterance-id1 "):
                is_transcript = True
                out.append(line[len(transcript_marker):])
            elif line.startswith("LOG"):
                is_transcript = False
            elif is_transcript:
                out.append(line)
        transcript = "\n".join(out)
        transcript = transcript \
            .replace("<unk>", "") \
            .replace("mm", "") \
            .replace("[noise]", "")
        return transcript

    class Meta:
        abstract = True
