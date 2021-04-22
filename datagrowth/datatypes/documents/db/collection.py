import json
from collections import Iterator, Iterable, defaultdict
from math import ceil
from datetime import datetime

from django.apps import apps
from django.db import models
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import make_aware

from datagrowth import settings as datagrowth_settings
from datagrowth.utils import ibatch, reach
from .base import DataStorage


class CollectionBase(DataStorage):

    name = models.CharField(max_length=255, null=True, blank=True)
    identifier = models.CharField(max_length=255, null=True, blank=True)
    referee = models.CharField(max_length=255, null=True, blank=True)

    @classmethod
    def get_document_model(cls):
        # This method should use "Document" with local app label and get_model function to load the model
        return apps.get_model("{}.Document".format(cls._meta.app_label))

    @property
    def documents(self):
        raise NotImplementedError("CollectionBase needs to implement the documents property to work correctly")

    @property
    def annotations(self):
        Annotation = apps.get_model("{}.Annotation".format(self._meta.app_label))
        return Annotation.objects.filter(reference__in=self.documents.values("reference"))

    def init_document(self, data, collection=None):
        Document = self.get_document_model()
        return Document(
            collection=collection,
            properties=data
        )

    @classmethod
    def validate(cls, data, schema):
        """
        Validates the data against given schema for one of more Documents.

        :param data: The data to validate
        :param schema: The JSON schema to use for validation.
        :return: Valid data
        """
        Document = cls.get_document_model()
        if not isinstance(data, Iterable):
            data = [data]
        for instance in data:
            Document.validate(instance, schema)

    def add(self, data, reset=False, batch_size=500, collection=None, modified_at=None, validate=True):
        """
        Add new data to the Collection in batches, possibly deleting all data before adding.

        :param data: The data to use for the update
        :param reset: (optional) whether to delete existing data or not (no by default)
        :param batch_size: (optional) how many instances to add in a single batch (default: 500)
        :param collection: (optional) a collection instance to add the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now)
        :param validate: (deprecated) used to allow JSON schema validation before addition
        :return: A list of updated or created instances.
        """
        collection = collection or self
        modified_at = modified_at or make_aware(datetime.now())
        Document = collection.get_document_model()
        assert isinstance(data, (Iterator, list, tuple, dict, Document)), \
            f"Collection.add expects data to be formatted as iteratable, dict or {type(Document)} not {type(data)}"

        if reset:
            self.documents.all().delete()

        def prepare_additions(data):

            prepared = []
            if isinstance(data, dict):
                document = self.init_document(data, collection=collection)
                document.clean()
                prepared.append(document)
            elif isinstance(data, Document):
                data = self.init_document(data.properties, collection=collection)
                data.clean()
                prepared.append(data)
            else:  # type is list
                for instance in data:
                    prepared += prepare_additions(instance)
            return prepared

        count = 0
        for additions in ibatch(data, batch_size=batch_size):
            additions = prepare_additions(additions)
            count += len(additions)
            Document.objects.bulk_create(additions, batch_size=datagrowth_settings.DATAGROWTH_MAX_BATCH_SIZE)

        if collection.modified_at.replace(microsecond=0) != modified_at.replace(microsecond=0):
            collection.modified_at = modified_at
            collection.save()
        return count

    def update(self, data, by_property, batch_size=32, collection=None, modified_at=None, validate=True):
        """
        Update data to the Collection in batches, using a property value to identify which Documents to update.

        :param data: The data to use for the update
        :param by_property: The property to identify a Document with
        :param batch_size: (optional) how many instances to add in a single batch (default: 32)
        :param collection: (optional) a collection instance to update the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now)
        :param validate: (deprecated) used to allow JSON schema validation before updates
        :return: A list of updated or created instances.
        """
        collection = collection or self
        modified_at = modified_at or make_aware(datetime.now())
        Document = collection.get_document_model()
        assert isinstance(data, (Iterator, list, tuple,)), \
            f"Collection.update expects data to be formatted as iteratable not {type(data)}"

        count = 0
        for updates in ibatch(data, batch_size=batch_size):
            # We bulk update by getting all objects whose property matches
            # any update's "by_property" property value and then updating these source objects.
            # One update object can potentially target multiple sources
            # if multiple objects with the same value for the by_property property exist.
            updated = set()
            prepared = []
            sources_by_lookup = defaultdict(list)
            for update in updates:
                sources_by_lookup[update[by_property]].append(update)
            target_filters = Q()
            for lookup_value in sources_by_lookup.keys():
                target_filters |= Q(**{f"properties__{by_property}": lookup_value})
            for target in collection.documents.filter(target_filters):
                for update_value in sources_by_lookup[target.properties[by_property]]:
                    target.update(update_value, commit=False)
                count += 1
                updated.add(target.properties[by_property])
                prepared.append(target)
            Document.objects.bulk_update(
                prepared,
                ["properties", "identity", "reference", "modified_at"],
                batch_size=datagrowth_settings.DATAGROWTH_MAX_BATCH_SIZE
            )
            # After all updates we add all data that hasn't been used in any update operation
            additions = []
            for lookup_value, sources in sources_by_lookup.items():
                if lookup_value not in updated:
                    additions += sources
            if len(additions):
                count += self.add(additions, batch_size=batch_size, collection=collection, modified_at=modified_at)

        if collection.modified_at.replace(microsecond=0) != modified_at.replace(microsecond=0):
            collection.modified_at = modified_at
            collection.save()
        return count

    @property
    def content(self):
        """
        Returns the content of the documents of this Collection

        :return: a generator yielding properties from Documents
        """
        return (doc.content for doc in self.documents.iterator())

    @property
    def has_content(self):
        """
        Indicates if Collection entails Documents or not

        :return: True if there are Documents, False otherwise
        """
        return self.documents.exists()

    def split(self, train=0.8, validate=0.1, test=0.1, query_set=None, as_content=False):
        assert train + validate + test == 1.0, "Expected sum of train, validate and test to be 1"
        assert train > 0, "Expected train set to be bigger than 0"
        assert validate > 0, "Expected validate set to be bigger than 0"
        query_set = query_set or self.documents
        content_count = query_set.count()
        # TODO: take into account that random ordering in MySQL is a bad idea
        # Details: http://www.titov.net/2005/09/21/do-not-use-order-by-rand-or-how-to-get-random-rows-from-table/
        documents = query_set.order_by("?").iterator()
        test_set = []
        if test:
            test_size = ceil(content_count * test)
            test_set = [next(documents) for ix in range(0, test_size)]
        validate_size = ceil(content_count * validate)
        validate_set = [next(documents) for ix in range(0, validate_size)]
        return (
            (document.content if as_content else document for document in documents),
            [document.content if as_content else document for document in validate_set],
            [document.content if as_content else document for document in test_set]
        )

    def output(self, *args):
        if len(args) > 1:
            return map(self.output, args)
        frm = args[0]
        if not frm:
            return [frm for doc in range(0, self.documents.count())]
        elif isinstance(frm, list):
            output = self.output(*frm)
            if len(frm) > 1:
                output = [list(zipped) for zipped in zip(*output)]
            else:
                output = [[out] for out in output]
            return output
        else:
            return [doc.output(frm) for doc in self.documents.iterator()]

    def group_by(self, key):
        """
        Outputs a dict with lists. The lists are filled with Documents that hold the same value for key.

        :param key:
        :return:
        """
        grouped = {}
        for doc in self.documents.all():
            assert key in doc.properties, \
                "Can't group by {}, because it is missing from an document in collection {}".format(key, self.id)
            value = doc.properties[key]
            if value not in grouped:
                grouped[value] = [doc]
            else:
                grouped[value].append(doc)
        return grouped

    def influence(self, document):
        """
        This allows the Collection to set some attributes and or properties on the Document

        :param document: The document that should be influenced
        :return: The influenced document
        """
        if self.identifier:
            document.identity = reach("$." + self.identifier, document.properties)
        if self.referee:
            document.reference = reach("$." + self.referee, document.properties)
        return document

    def to_file(self, file_path):
        with open(file_path, "w") as json_file:
            json.dump(list(self.content), json_file, cls=DjangoJSONEncoder)

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ["id"]


class DocumentCollectionMixin(object):

    @property
    def documents(self):
        return self.document_set
