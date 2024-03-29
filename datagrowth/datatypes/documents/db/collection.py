import json
from collections import defaultdict
from collections.abc import Iterator, Iterable
from math import ceil
from datetime import datetime
import warnings

from django.apps import apps
from django.db import models
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import make_aware

from datagrowth import settings as datagrowth_settings
from datagrowth.utils import ibatch, reach, is_hashable
from datagrowth.datatypes.storage import DataStorage


NO_MODIFICATION = object()


class CollectionBase(DataStorage):

    dataset_version = models.ForeignKey("DatasetVersion", null=True, blank=True, on_delete=models.CASCADE)

    name = models.CharField(max_length=255, null=True, blank=True)
    identifier = models.CharField(max_length=255, null=True, blank=True)
    referee = models.CharField(max_length=255, null=True, blank=True)

    @property
    def documents(self):
        raise NotImplementedError("CollectionBase needs to implement the documents property to work correctly")

    @property
    def annotations(self):
        Annotation = apps.get_model("{}.Annotation".format(self._meta.app_label))
        return Annotation.objects.filter(reference__in=self.documents.values("reference"))

    def build_document(self, data, collection=None):
        if hasattr(self, "init_document"):
            warnings.warn("Collection.init_document method is deprecated in favour of Collection.build_document",
                          DeprecationWarning)
            document = self.init_document(data, collection)
            document.clean()  # this gets handles by Document.build, but not by the legacy Collection.init_document
            return document
        Document = self.get_document_model()
        return Document.build(data, collection=collection or self)

    @property
    def document_update_fields(self):
        """
        Specified which fields on Document are required to update in bulk_update operations

        :return list: field names
        """
        return [
            "properties", "derivatives", "task_results", "identity", "reference",
            "modified_at", "pending_at", "finished_at"
        ]

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

    def reload_document_ids(self, documents):
        """
        Reloads given documents from the database if ``identifier`` is set. Reloaded documents always have an id.
        Unfortunately MySQL doesn't work well with Django's batch create,
        because ids won't be set for MySQL when using batch_create.
        This method is here to provide a workaround for MySQL,
        because sometimes having ids of new instances is required.
        Using ``reload_document_ids`` on Documents that have ids does nothing.

        :param documents: the documents that may or may not have ids
        :return: the documents with ids
        """
        assert self.identifier, "Can't reload document ids if Collection is not setting Document identity"
        reloaded = []
        document_identities = []
        for document in documents:
            if document.id:
                reloaded.append(document)
            elif document.identity is None:
                raise ValueError("Can't reload document id if identity is unknown")
            else:
                document_identities.append(document.identity)
        if len(document_identities):
            Document = self.get_document_model()
            reloaded += Document.objects.filter(identity__in=document_identities)
        return reloaded

    def add(self, data, reset=False, collection=None, modified_at=None):
        """
        Add new data to the Collection, possibly deleting all data before adding.
        This method will load all data into memory before inserting it into the database.
        Use ``add_batches`` for a more memory footprint friendly version.

        :param data: The data to use for the inserts
        :param reset: (optional) whether to delete existing data or not (no by default)
        :param collection: (optional) a collection instance to add the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now).
            Alternatively the NO_MODIFICATION sentient object can be passed to prevent alteration of modified_at.
        :return: A list of created instances.
        """
        batches = self.add_batches(
            data,
            reset=reset,
            collection=collection,
            modified_at=modified_at
        )
        additions = []
        for batch in batches:
            additions += batch
        return additions

    def add_batches(self, data, batch_size=None, reset=False, collection=None, modified_at=None):
        """
        Add new data to the Collection, possibly deleting all data before adding.

        :param data: The data to use for the inserts
        :param batch_size: The amount of objects to load in memory and insert at once
        :param reset: (optional) whether to delete existing data or not (no by default)
        :param collection: (optional) a collection instance to add the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now).
            Alternatively the NO_MODIFICATION sentient object can be passed to prevent alteration of modified_at.
        :return: An iterator of batches with created instances.
        """
        batch_size = batch_size or datagrowth_settings.DATAGROWTH_MAX_BATCH_SIZE
        collection = collection or self
        modified_at = modified_at or make_aware(datetime.now())
        Document = collection.get_document_model()
        assert isinstance(data, (Iterator, list, tuple,)), \
            f"Collection.add expects data to be formatted as sequential iterable not {type(data)}"

        if reset:
            self.documents.all().delete()

        def prepare_additions(initial_data):

            prepared = []
            if isinstance(initial_data, dict):
                document = self.build_document(initial_data, collection=collection)
                prepared.append(document)
            elif isinstance(initial_data, Document):
                document = self.build_document(initial_data.properties, collection=collection)
                if hasattr(initial_data, "task_results"):
                    document.task_results = initial_data.task_results
                    document.derivatives = initial_data.derivatives
                prepared.append(document)
            else:  # type is list
                for instance in initial_data:
                    prepared += prepare_additions(instance)
            return prepared

        # Make instances in data unique by hash to prevent adding instances with identical hashes
        # This is mostly relevant for models that override the __hash__ method,
        # because Django won't delete instances with identical hashes even when using Document.objects.all().delete().
        # We can't force uniqueness for Iterator based updates, because that would mean loading all instances in memory.
        if isinstance(data, list) and len(data):
            unique_instances = {
                obj if is_hashable(obj) else ix: obj
                for ix, obj in enumerate(data)
            }
            data = list(unique_instances.values())

        for additions in ibatch(data, batch_size=batch_size):
            additions = prepare_additions(additions)
            yield Document.objects.bulk_create(additions, batch_size=batch_size)

        if modified_at is not NO_MODIFICATION and \
                collection.modified_at.replace(microsecond=0) != modified_at.replace(microsecond=0):
            collection.modified_at = modified_at
            collection.save()

    def update(self, data, by_property, collection=None, modified_at=None):
        """
        Update data to the Collection, using a property value to identify which Documents to update.
        Any data that does not exist will be added instead.
        This method will load all data into memory before performing upserts into the database.
        Use ``update_batches`` for a more memory footprint friendly version.

        :param data: The data to use for the upsert
        :param by_property: The property to identify a Document with
        :param collection: (optional) a collection instance to upsert the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now).
            Alternatively the NO_MODIFICATION sentient object can be passed to prevent alteration of modified_at.
        :return: A list of updated or created instances.
        """
        batches = self.update_batches(
            data,
            by_property=by_property,
            collection=collection,
            modified_at=modified_at
        )
        upserts = []
        for batch in batches:
            upserts += batch
        return upserts

    def update_batches(self, data, by_property, batch_size=32, collection=None, modified_at=None):
        """
        Update data to the Collection, using a property value to identify which Documents to update.
        Any data that does not exist will be added instead.

        :param data: The data to use for the upsert
        :param by_property: The property to identify a Document with
        :param batch_size: The amount of objects to load in memory and insert at once
        :param collection: (optional) a collection instance to upsert the data to (default: self)
        :param modified_at: (optional) the datetime to use as modified_at value for the collection (default: now).
            Alternatively the NO_MODIFICATION sentient object can be passed to prevent alteration of modified_at.
        :return: An iterator of batches with updated or created instances.
        """
        batch_size = batch_size or datagrowth_settings.DATAGROWTH_MAX_BATCH_SIZE
        collection = collection or self
        modified_at = modified_at or make_aware(datetime.now())
        Document = collection.get_document_model()
        assert isinstance(data, (Iterator, list, tuple,)), \
            f"Collection.update expects data to be formatted as iteratable not {type(data)}"

        for update_data in ibatch(data, batch_size=batch_size):
            # We bulk update by getting all objects whose property matches
            # any update's "by_property" property value and then updating these source objects.
            # One update object can potentially target multiple sources
            # if multiple objects with the same value for the by_property property exist.
            exists = set()
            updates = []
            sources_by_lookup = defaultdict(list)
            for update in update_data:
                # If input is a dict we cast it to Document to allow __eq__ methods to do their job.
                if isinstance(update, dict):
                    update = self.build_document(update, collection=collection)
                sources_by_lookup[update[by_property]].append(update)
            target_filters = Q()
            for lookup_value in sources_by_lookup.keys():
                target_filters |= Q(**{f"properties__{by_property}": lookup_value})
            for target in collection.documents.filter(target_filters):
                has_update = False
                for update_value in sources_by_lookup[target.properties[by_property]]:
                    if target != update_value:  # this will be False unless a __eq__ override decides otherwise
                        has_update = True
                        target.update(update_value, commit=False)
                exists.add(target.properties[by_property])
                if has_update:
                    updates.append(target)
            Document.objects.bulk_update(updates, self.document_update_fields, batch_size=batch_size)
            # After all updates we add all data that hasn't been used in any update operation
            additions = []
            for lookup_value, sources in sources_by_lookup.items():
                if lookup_value not in exists:
                    additions += sources
            if len(additions):
                additions = self.add(additions, collection=collection, modified_at=NO_MODIFICATION)
            yield updates + additions

        if modified_at is not NO_MODIFICATION and \
                collection.modified_at.replace(microsecond=0) != modified_at.replace(microsecond=0):
            collection.modified_at = modified_at
            collection.save()

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
        if self.dataset_version:
            self.dataset_version.influence(document)
        return document

    def to_file(self, file_path):
        with open(file_path, "w") as json_file:
            json.dump(list(self.content), json_file, cls=DjangoJSONEncoder)

    def clean(self):
        if self.dataset_version:
            self.dataset_version.influence(self)

    def __str__(self):
        return self.name if self.name else super().__str__()

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ["id"]


class DocumentCollectionMixin(object):

    @property
    def documents(self):
        return self.document_set
