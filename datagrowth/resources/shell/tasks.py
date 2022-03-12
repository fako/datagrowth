import logging
from time import sleep

from django.apps import apps
from celery import current_app as app

from datagrowth.configuration import load_config
from datagrowth.exceptions import DGResourceException


log = logging.getLogger("datascope")


@app.task(name="shell_resource.run")
@load_config()
def run(config, *args, **kwargs):
    # Set vars
    success = []
    errors = []
    Resource = apps.get_model(config.resource)
    cmd = Resource(config=config.to_dict(protected=True))
    # Run the command
    try:
        cmd = cmd.run(*args, **kwargs)
        cmd.close()
        success.append(cmd.id)
    except DGResourceException as exc:
        log.debug(exc)
        cmd = exc.resource
        cmd.close()
        errors.append(cmd.id)

    # Output results in simple type for json serialization
    return [success, errors]


@app.task(name="shell_resource.run_serie")
@load_config()
def run_serie(config, args_list, kwargs_list):
    success = []
    errors = []
    for args, kwargs in zip(args_list, kwargs_list):
        scc, err = run(config=config, *args, **kwargs)
        success += scc
        errors += err
    return [success, errors]
