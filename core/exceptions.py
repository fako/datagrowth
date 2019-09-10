from datagrowth.exceptions import (
    DGResourceException as DSResourceException,
    DGNoContent as DSNoContent,
    DGInvalidResource as DSInvalidResource
)


class DSHttpError400NoToken(DSResourceException):
    pass


class DSHttpWarning300(DSResourceException):
    pass


class DSProcessException(Exception):
    pass


class DSProcessUnfinished(DSProcessException):
    pass


class DSProcessError(DSProcessException):
    pass


class DSSystemConfigError(Exception):
    pass


class DSFileLoadError(Exception):
    pass
