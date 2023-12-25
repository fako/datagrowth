from django.test import TestCase

from datagrowth.resources.utils import serialize_resources, update_serialized_resources

from resources.models import HttpResourceMock, ShellResourceMock


class TestResourceUtils(TestCase):

    fixtures = ["test-http-resource-mock", "test-shell-resource-mock"]

    def test_serialize_http_resources(self):
        # Single Resource instance
        http = HttpResourceMock.objects.first()
        resource_info = serialize_resources(http)
        self.assertEqual(resource_info, {
            "success": True,
            "resource": "resources.httpresourcemock",
            "id": 1,
            "ids": [1]
        })
        # Multiple Resource instances
        http2 = HttpResourceMock.objects.last()
        resource_info = serialize_resources([http, http2])
        self.assertEqual(resource_info, {
            "success": True,
            "resource": "resources.httpresourcemock",
            "id": 1,
            "ids": [1, 9]
        })
        # With error instance
        http2.status = 404
        resource_info = serialize_resources([http, http2])
        self.assertEqual(resource_info, {
            "success": False,
            "resource": "resources.httpresourcemock",
            "id": 1,
            "ids": [1, 9]
        })

    def test_serialize_shell_resource(self):
        # Single Resource instance
        shell = ShellResourceMock.objects.first()
        resource_info = serialize_resources(shell)
        self.assertEqual(resource_info, {
            "success": True,
            "resource": "resources.shellresourcemock",
            "id": 1,
            "ids": [1]
        })
        # Multiple Resource instances
        shell2 = ShellResourceMock.objects.last()
        resource_info = serialize_resources([shell, shell2])
        self.assertEqual(resource_info, {
            "success": False,
            "resource": "resources.shellresourcemock",
            "id": 1,
            "ids": [1, 2]
        })
        # Without error instance
        shell2.status = 0
        shell2.stdout = "output"
        resource_info = serialize_resources([shell, shell2])
        self.assertEqual(resource_info, {
            "success": True,
            "resource": "resources.shellresourcemock",
            "id": 1,
            "ids": [1, 2]
        })

    def test_serialize_no_resources(self):
        resource_info = serialize_resources()
        self.assertEqual(resource_info, {
            "success": False,
            "resource": None,
            "id": None,
            "ids": []
        })

    def test_update_http_resource(self):
        http = HttpResourceMock.objects.first()
        serialization = {
            "resources.httpresourcemock": serialize_resources(http)
        }
        # Add a new Resource
        http2 = HttpResourceMock.objects.last()
        update_serialized_resources(serialization, [http2])
        self.assertEqual(serialization, {
            "resources.httpresourcemock": {
                "success": True,
                "resource": "resources.httpresourcemock",
                "id": 1,
                "ids": [1, 9]
            }
        })
        # Add an already added Resource with errors
        http.status = 404
        update_serialized_resources(serialization, http)
        self.assertEqual(serialization, {
            "resources.httpresourcemock": {
                "success": False,
                "resource": "resources.httpresourcemock",
                "id": 1,
                "ids": [1, 9, 1]
            }
        })

    def test_update_shell_resource(self):
        shell = ShellResourceMock.objects.first()
        serialization = {
            "resources.shellresourcemock": serialize_resources(shell)
        }
        # Add a new Resource
        shell2 = ShellResourceMock.objects.last()
        update_serialized_resources(serialization, [shell2])
        self.assertEqual(serialization, {
            "resources.shellresourcemock": {
                "success": False,
                "resource": "resources.shellresourcemock",
                "id": 1,
                "ids": [1, 2]
            }
        })
        # Add an already added Resource
        update_serialized_resources(serialization, shell)
        self.assertEqual(serialization, {
            "resources.shellresourcemock": {
                "success": False,
                "resource": "resources.shellresourcemock",
                "id": 1,
                "ids": [1, 2, 1]
            }
        })
