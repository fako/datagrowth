try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

from datagrowth.datatypes import DocumentBase


class Document(DocumentBase):
    pass
