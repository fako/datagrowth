from typing import Type
import os
from collections import defaultdict

from django.core.management.base import CommandError
from django.core.management.commands.loaddata import Command as LoadDataCommand
from django.core import serializers
from django.core.management.color import no_style
from django.db import connection

from datagrowth.configuration import register_defaults
from datagrowth.resources.base import Resource
from datagrowth.resources.http import HttpResource
from datagrowth.resources.shell import ShellResource


class EnableGlobalCacheMixin:

    noCache = False

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()  # type: ignore[reportAttributeAccessIssue]
        if not cls.noCache:
            register_defaults("global", {
                "cache_only": True
            })

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.noCache:
            register_defaults("global", {
                "cache_only": False
            })
        super().tearDownClass()  # type: ignore[reportAttributeAccessIssue]


class ResourceFixturesMixin(EnableGlobalCacheMixin):

    resource_fixtures = []

    _loaded_resource_ids = defaultdict(list)

    @classmethod
    def read_resource_attribute_fixture(cls, fixture_dir, resource, attribute):
        file_name = getattr(resource, attribute)
        if not file_name:
            return
        attribute_file_path = os.path.join(fixture_dir, file_name)
        if not os.path.exists(attribute_file_path):
            raise FileNotFoundError(f"Can't find resource fixture: {file_name}")
        with open(attribute_file_path, "r") as attribute_file:
            content = attribute_file.read()
            setattr(resource, attribute, content)

    @classmethod
    def setUpTestData(cls):
        # Calling super just in case some extra data gets added
        super().setUpTestData()  # type: ignore[reportAttributeAccessIssue]
        # Setting up the loaddata command in code to help with scanning for fixtures
        load_data = LoadDataCommand()
        load_data.app_label = None  # type: ignore[reportAttributeAccessIssue]
        load_data.using = "default"
        load_data.compression_formats = {
            None: (open, 'rb'),  # type: ignore[reportAttributeAccessIssue]
        }
        load_data.serialization_formats = serializers.get_public_serializer_formats()
        load_data.verbosity = 0
        # Actual searching for fixture files that are in a fixtures/resources directory
        for fixture_dir in load_data.fixture_dirs:
            resources_fixture_dir = os.path.join(fixture_dir, "resources")
            if not os.path.exists(resources_fixture_dir):
                continue
            resource_fixture_labels = [
                os.path.join(resources_fixture_dir, resource_fixture)
                for resource_fixture in cls.resource_fixtures
            ]
            for resource_fixture_label in resource_fixture_labels:
                # Loading of fixture objects, this is mostly copied from loaddata command
                try:
                    for file_path, directory, file_name in load_data.find_fixtures(resource_fixture_label):
                        _, ser_fmt, cmp_fmt = load_data.parse_name(os.path.basename(file_path))
                        open_method, mode = load_data.compression_formats[cmp_fmt]  # type: ignore[reportArgumentType]
                        fixture = open_method(file_path, mode)
                        objects = serializers.deserialize(
                            ser_fmt, fixture,  # type: ignore[reportArgumentType]
                            using=load_data.using, ignorenonexistent=False,
                            handle_forward_references=True,
                        )
                        for obj in objects:
                            if isinstance(obj.object, HttpResource):
                                cls.read_resource_attribute_fixture(directory, obj.object, "body")
                            elif isinstance(obj.object, ShellResource):
                                cls.read_resource_attribute_fixture(directory, obj.object, "stdout")
                                cls.read_resource_attribute_fixture(directory, obj.object, "stderr")
                            else:
                                raise TypeError(f"Unexpected Resource type for loading content: {type(obj.object)}")
                            obj.save()
                            cls._loaded_resource_ids[obj.object.__class__].append(obj.object.id)
                except CommandError:
                    pass

        # Reset sequences for all touched models so future inserts with id=None get a PK in line with the sequence
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), list(cls._loaded_resource_ids.keys())):
                cursor.execute(sql)

    @classmethod
    def print_new_resources(cls, resource_type: Type[Resource]) -> None:
        ids = cls._loaded_resource_ids.get(resource_type, [])
        new_data = serializers.serialize("json", resource_type.objects.exclude(id__in=ids), indent=4)
        print(new_data)
