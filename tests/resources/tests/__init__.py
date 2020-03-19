from .http.core import TestHttpResource
from .http.generic import TestHttpResourceInterface
from .http.url import TestURLResourceInterface
from .http.files import TestHttpImageResourceInterface
from .http.micro import TestMicroServiceResourceInterface
from .http.tasks import (TestSendMassTaskGet, TestSendMassTaskPost, TestSendTaskGet, TestSendTaskPost,
                         TestSendSerieTaskGet, TestSendSerieTaskPost, TestGetResourceLink, TestLoadSession)

from .shell.core import TestShellResource
from .shell.generic import TestShellResourceInterface
