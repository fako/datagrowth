import logging
from datetime import timedelta
from time import sleep

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, ContentType
from django.utils.timezone import now

from datagrowth import configuration


log = logging.getLogger("datascope")


class Resource(models.Model):
    """
    This class defines the interface that all resources adhere to.
    You'll rarely extend this class directly.
    The ``HttpResource`` and ``ShellResource`` are examples of classes that overextend this class.
    """

    # Identification
    uri = models.CharField(max_length=255, db_index=True, default=None)
    status = models.PositiveIntegerField(default=0)

    # Configuration
    config = configuration.ConfigurationField()

    # Archiving fields
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    purge_at = models.DateTimeField(null=True, blank=True)

    # Retention
    retainer = GenericForeignKey(ct_field="retainer_type", fk_field="retainer_id")
    retainer_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    retainer_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ("id",)

    def __init__(self, *args, **kwargs):
        self.interval_duration = kwargs.pop("interval_duration", 0)
        super(Resource, self).__init__(*args, **kwargs)

    def clean(self):
        if self.uri and len(self.uri):
            self.uri = self.uri[:255]
        if not self.id and self.config.purge_immediately:
            self.purge_at = now()
        if not self.purge_at and self.config.purge_after:
            self.purge_at = now() + timedelta(**self.config.purge_after)

    #######################################################
    # RESOURCE INTERFACE
    #######################################################
    # A set of methods and properties shared by resources
    # This interface allows to generically handle data

    def close(self):
        """
        This convenience method handles both the clean and save step for saving models.
        To make use of the resource cache it's necessary to clean before saving and close handles this directly.
        """
        self.clean()
        self.save()

    def retain(self, retainer):
        """
        Links any Django model unto a ``GenericRelation`` upon a resource.
        Any resources retained this way will not get deleted from cache.
        This is convenient to save any context that can help during debugging.

        :param retainer: (model) the model retaining the resource
        """
        self.retainer = retainer
        self.close()

    @classmethod
    def get_name(cls):
        """
        Return the name of the resource. This is the model_name for almost all resources.

        :return: (str) lowercase model name
        """
        return cls._meta.model_name

    @classmethod
    def get_queue_name(cls):
        """
        Returns the queue name that background tasks should dispatch to.
        By default it returns the default Django Celery queue name.

        :return: (str) queue name
        """
        return getattr(settings, "CELERY_TASK_DEFAULT_QUEUE", "celery")

    @property
    def content(self):
        """
        This method typically gets overwritten for different resource types.
        It should return the content_type and data from the resource.

        :return: content_type, data
        """
        raise NotImplementedError("Missing implementation for content property on {}".format(self.__class__.__name__))

    @property
    def success(self):
        """
        This method typically gets overwritten for different resource types.
        It should indicate the success of the data gathering.

        :return: (bool)
        """
        raise NotImplementedError("Missing implementation for content property on {}".format(self.__class__.__name__))

    #######################################################
    # RESOURCE ABSTRACTION
    #######################################################
    # A set of methods and properties shared by resources
    # This interface often needs source specific overrides

    def handle_errors(self):
        """
        Overwrite this method to handle resource specific error cases.
        Usually you'd raise a particular ``DGResourceException`` to indicate particular errors.
        """
        raise NotImplementedError(
            "Missing implementation for handle_errors method on {}".format(self.__class__.__name__)
        )

    def variables(self, *args):
        """
        Maps the input arguments from a resource to a dictionary.
        This makes it easy to access the positional input variables under names.
        Overwrite this method to create the mapping for your particular resource.

        :param args: (tuple) the positional arguments given as input to the resource
        :return: (dict) a dictionary with the input variables as values
        """
        raise NotImplementedError("Missing implementation for variables method on {}".format(self.__class__.__name__))
