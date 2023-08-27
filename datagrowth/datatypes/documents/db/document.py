from itertools import repeat
import warnings
from datetime import datetime

import jsonschema
from jsonschema.exceptions import ValidationError as SchemaValidationError

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField


from datagrowth.utils import reach
from .base import DataStorage


class DocumentBase(DataStorage):

    properties = JSONField(default=dict)

    collection = models.ForeignKey("Collection", blank=True, null=True, on_delete=models.CASCADE)
    identity = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    reference = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value

    @classmethod
    def build(cls, data, collection=None):
        """
        Build a new Document without committing to the database.
        Will perform a clean to correctly set attributes based on input data.

        :param data: The data to set as properties of the new Document
        :param collection: The collection for the new Document
        :return:
        """
        instance = cls(properties=data, collection=collection)
        instance.clean()
        return instance

    @staticmethod
    def validate(data, schema):
        """
        Validates the data against given schema

        :param data: The data to validate
        :param schema: The JSON schema to use for validation.
        :return: Valid data
        """

        if isinstance(data, dict):
            properties = data
        elif isinstance(data, DocumentBase):
            properties = data.properties
        else:
            raise ValidationError(
                "An Document can only work with a dict as data and got {} instead".format(type(data))
            )
        if "_id" in properties:
            del properties["_id"]

        try:
            jsonschema.validate(properties, schema)
        except SchemaValidationError as exc:
            django_exception = ValidationError(exc.message)
            django_exception.schema = exc.schema
            raise django_exception

    def update(self, data, commit=True):
        """
        Update the properties with new data.

        :param data: The data to use for the update
        :param commit: Whether to commit new values to the database or not
        :return: Updated content
        """
        content = data.properties if isinstance(data, DocumentBase) else data
        self.properties.update(content)
        self.clean()
        if commit:
            self.save()
        else:
            self.modified_at = make_aware(datetime.now())
        return self.content

    @property
    def content(self):
        """
        Returns the content of this Document

        :return: Dictionary filled with properties.
        """
        return dict(
            {key: value for key, value in self.properties.items() if not key.startswith('_')},
            _id=self.id
        )

    def output(self, *args):
        return self.output_from_content(self.content, *args)

    @staticmethod
    def output_from_content(content, *args, replacement_character="$"):
        # Assert and abbreviate the replacement_character input
        assert replacement_character != "\\", "Can't use '\' as a replacement character"
        rpl = replacement_character
        # When dealing with multiple args we'll handle it one by one using map function
        if len(args) > 1:
            mapping = map(
                lambda cnt, arg: DocumentBase.output_from_content(cnt, arg, replacement_character=rpl),
                repeat(content), args
            )
            return list(mapping)
        # From here we'll check different types of the input and return values accordingly
        frm = args[0]
        if not frm:
            return frm
        # This is the case that matters most. It replaces a JSON path with a value from the input content
        if isinstance(frm, str) and frm.startswith(replacement_character):
            frm = frm.replace(rpl, "$", 1)
            return reach(frm, content)
        # When dealing with a list as args we'll recursively call this function
        # Making sure that we'll always return a list
        elif isinstance(frm, list):
            if len(frm) > 1:
                return DocumentBase.output_from_content(content, *frm, replacement_character=rpl)
            else:
                return [DocumentBase.output_from_content(content, *frm, replacement_character=rpl)]
        # When dealing with a dict as args we'll recursively call this function on the values
        # and make sure we always return a dict
        elif isinstance(frm, dict):
            return {
                key: DocumentBase.output_from_content(content, value, replacement_character=rpl)
                for key, value in frm.items()
            }
        # We'll remove any backslash characters from the start of strings
        elif isinstance(frm, str) and frm.startswith(f"\\"):
            frm = frm.replace("\\", "", 1)
        # Passing along input as-is
        return frm

    def items(self):
        return self.properties.items()

    def keys(self):
        return self.properties.keys()

    def values(self):
        return self.properties.values()

    def clean(self):
        # Always influence first!
        if self.collection:
            self.collection.influence(self)
        # After influence check integrity
        identity_max_length = DocumentBase._meta.get_field('identity').max_length
        if self.identity and isinstance(self.identity, str) and len(self.identity) > identity_max_length:
            self.identity = self.identity[:identity_max_length]

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ["id"]


class DocumentMysql(models.Model):

    properties = JSONField(default=dict)

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        warnings.warn(
            "Subclassing the DocumentMySQL mixin is deprecated inherit from DocumentBase instead",
            DeprecationWarning
        )

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ["id"]


class DocumentPostgres(models.Model):

    properties = JSONField(default=dict)

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        warnings.warn(
            "Subclassing the DocumentPostgres mixin is deprecated inherit from DocumentBase instead",
            DeprecationWarning
        )

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ["id"]
