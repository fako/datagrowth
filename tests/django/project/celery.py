import os

from django.apps import apps
from django.core.wsgi import get_wsgi_application
from celery import Celery


app = Celery('project')

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
application = get_wsgi_application()  # load the apps

app.autodiscover_tasks(lambda: [cfg.name for cfg in apps.get_app_configs()], force=True)
