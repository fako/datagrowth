import os

from django.core.management.base import CommandError
from django.core.management.commands.loaddata import Command as LoadDataCommand
from django.core import serializers

from datagrowth.resources.http import HttpResource
from datagrowth.resources.shell import ShellResource


class ResourceFixturesMixin:

    resource_fixtures = []

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
        super().setUpTestData()
        # Setting up the loaddata command in code to help with scanning for fixtures
        load_data = LoadDataCommand()
        load_data.app_label = None
        load_data.using = "default"
        load_data.compression_formats = {
            None: (open, 'rb'),
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
                        open_method, mode = load_data.compression_formats[cmp_fmt]
                        fixture = open_method(file_path, mode)
                        objects = serializers.deserialize(
                            ser_fmt, fixture, using=load_data.using, ignorenonexistent=False,
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
                except CommandError:
                    pass
