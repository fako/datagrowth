import requests

from datagrowth.configuration import ConfigurationType
from datagrowth.processors.base import Processor


def load_session():
    """
    This decorator will try to fetch a session object based on the "session" keyword argument.
    If the argument is a string it is assumed to be the name of a processor that implements the get_session method.
    Whatever this method returns gets injected under the "session" keyword argument for the decorated function.
    If the argument is not a string it gets returned as being a valid session for the resource.

    :param defaults: (mixed) Name of the session provider or the session object.
    :return:
    """
    def wrap(func):
        def session_func(config, *args, **kwargs):
            assert isinstance(config, ConfigurationType), \
                "load_session expects a fully prepared ConfigurationType for config"
            session_injection = kwargs.pop("session", None)
            if not session_injection:
                session_injection = requests.Session()
            if not isinstance(session_injection, str):
                return func(config, session=session_injection, *args, **kwargs)
            session_provider = Processor.get_processor_class(session_injection)
            session = session_provider.get_session(config)
            return func(config, session=session, *args, **kwargs)
        return session_func
    return wrap
