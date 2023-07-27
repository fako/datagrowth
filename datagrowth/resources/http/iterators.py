import logging

from django.apps import apps

from datagrowth.configuration import ConfigurationType, load_config
from datagrowth.exceptions import DGResourceException
from datagrowth.resources.http import load_session


log = logging.getLogger("datascope")


def get_resource_link(config, session=None):
    assert isinstance(config, ConfigurationType), \
        "get_resource_link expects a fully prepared ConfigurationType for config"
    Resource = apps.get_model(config.resource)
    link = Resource(config=config.to_dict(protected=True))

    if session is not None:
        link.session = session
    assert link.session, "Http resources require a session object to get a link object."
    token = getattr(link.session, "token", None)
    if token:
        link.token = session.token
    # FEATURE: update session to use proxy when configured
    return link


@load_config()
@load_session()
def send_iterator(config, *args, **kwargs):
    # Set vars
    session = kwargs.pop("session", None)
    method = kwargs.pop("method", None)
    has_next_request = True
    current_request = {}
    count = 0
    limit = config.continuation_limit or 1
    # Continue as long as there are subsequent requests
    while has_next_request and count < limit:
        # Get payload
        link = get_resource_link(config, session)
        link.request = current_request
        link.interval_duration = config.interval_duration
        try:
            link = link.send(method, *args, **kwargs)
            link.close()
        except DGResourceException as exc:
            log.debug(exc)
            link = exc.resource
            link.close()
        # Prepare next request
        has_next_request = current_request = link.create_next_request()
        count += 1
        yield link


@load_config()
@load_session()
def send_serie_iterator(config, args_list, kwargs_list, method=None, session=None):
    for args, kwargs in zip(args_list, kwargs_list):
        for resource in send_iterator(method=method, config=config, session=session, *args, **kwargs):
            yield resource
