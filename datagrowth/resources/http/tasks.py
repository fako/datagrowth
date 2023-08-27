import logging

from django.apps import apps
from celery import current_app as app

from datagrowth.configuration import ConfigurationType, load_config
from datagrowth.resources.http import load_session
from datagrowth.resources.http import send_iterator


log = logging.getLogger("datagrowth")


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


@app.task(name="http_resource.send")
@load_config()
@load_session()
def send(config, *args, **kwargs):
    # Set vars
    session = kwargs.pop("session", None)
    method = kwargs.pop("method", None)
    success = []
    errors = []
    # Send initial Resource as well as any followup Resources and iterator over all of them
    for link in send_iterator(method=method, config=config, session=session, *args, **kwargs):
        if link.success:
            success.append(link.id)
        else:
            errors.append(link.id)
    # Output results in simple type for json serialization
    return [success, errors]


@app.task(name="http_resource.send_serie")
@load_config()
@load_session()
def send_serie(config, args_list, kwargs_list, session=None, method=None):
    success = []
    errors = []
    for args, kwargs in zip(args_list, kwargs_list):
        # Get the results
        scc, err = send(method=method, config=config, session=session, *args, **kwargs)
        success += scc
        errors += err
    return [success, errors]


@app.task(name="http_resource.send_mass")
@load_config()
@load_session()
def send_mass(config, args_list, kwargs_list, session=None, method=None):

    assert args_list and kwargs_list, "No args list and/or kwargs list given to send mass"

    if config.concat_args_size:
        # Set some vars based on config
        symbol = config.concat_args_symbol
        concat_size = config.concat_args_size
        args_list_size = int(len(args_list) / concat_size) + 1
        # Calculate new args_list and kwargs_list
        # Arg list that are of the form [[1],[2],[3], ...] should become [[1|2|3], ...]
        # Kwargs are assumed to remain similar across the list
        prc_args_list = []
        prc_kwargs_list = []
        for index in range(0, args_list_size):
            args_slice = args_list[index*concat_size:index*concat_size+concat_size]
            joined_slice = []
            for args in args_slice:
                joined = symbol.join(map(str, args))
                joined_slice.append(joined)
            prc_args_list.append([symbol.join(joined_slice)])
            prc_kwargs_list.append(kwargs_list[0])
    else:
        prc_args_list = args_list
        prc_kwargs_list = kwargs_list

    return send_serie(
        prc_args_list,
        prc_kwargs_list,
        config=config,
        method=method,
        session=session
    )
