class DGResourceException(Exception):

    def __init__(self, message, resource):
        super().__init__(message)
        self.resource = resource


class DGShellError(DGResourceException):
    pass


class DGHttpError50X(DGResourceException):
    pass


class DGHttpError40X(DGResourceException):
    pass


class DGNoContent(Exception):
    pass


class DGHttpError403LimitExceeded(DGResourceException):
    pass


class DGHttpWarning204(DGResourceException):
    pass


class DGInvalidResource(DGResourceException):
    pass


class DGHttpError400NoToken(DGResourceException):
    pass


class DGHttpWarning300(DGResourceException):
    pass


class DGResourceDoesNotExist(DGResourceException):
    pass


class DGGrowthException(Exception):
    pass


class DGGrowthUnfinished(DGGrowthException):
    pass


class DGGrowthFrozen(DGGrowthException):
    pass


class DGGrowthError(DGGrowthException):
    pass


class DGPendingDataStorage(Exception):
    pass


class DGPendingDocuments(DGPendingDataStorage):
    pass


class DGPendingCollections(DGPendingDataStorage):
    pass
