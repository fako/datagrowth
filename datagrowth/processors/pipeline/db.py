from django.db import models


class ProcessResultBase(models.Model):

    class Meta:
        abstract = True
