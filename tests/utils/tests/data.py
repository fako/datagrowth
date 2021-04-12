from unittest import TestCase

from datagrowth.utils import reach, override_dict, is_json_mimetype


class TestPythonReach(TestCase):

    def setUp(self):
        super().setUp()
        self.test_dict = {
            "dict": {
                "test": "nested value",
                "list": ["nested value 0", "nested value 1", "nested value 2"],
                "dict": {"test": "test"}
            },
            "list": ["value 0", "value 1", "value 2"],
            "dotted.key": "another value"
        }
        self.test_list = [
            {"test": "dict in list"}
        ]

    def test_dict_access(self):
        self.assertEqual(reach("$.dict.test", self.test_dict), self.test_dict["dict"]["test"])
        self.assertEqual(reach("$.dict.dict", self.test_dict), self.test_dict["dict"]["dict"])
        self.assertEqual(reach("$.dict.list", self.test_dict), self.test_dict["dict"]["list"])

    def test_list_access(self):
        self.assertEqual(reach("$.list.0", self.test_dict), self.test_dict["list"][0])
        self.assertEqual(reach("$.dict.list.0", self.test_dict), self.test_dict["dict"]["list"][0])
        self.assertEqual(reach("$.0.test", self.test_list), self.test_list[0]["test"])

    def test_key_with_dots(self):
        self.assertEqual(reach("$.dotted.key", self.test_dict), self.test_dict["dotted.key"])

    def test_invalid_key(self):
        self.assertEqual(reach("$.does.not.exist", self.test_dict), None)

    def test_none_and_dollar_key(self):
        self.assertEqual(reach(None, self.test_dict), self.test_dict)
        self.assertEqual(reach(None, self.test_list), self.test_list)
        self.assertEqual(reach("$", self.test_dict), self.test_dict)
        self.assertEqual(reach("$", self.test_list), self.test_list)

    def test_invalid_data(self):
        try:
            reach("$.irrelevant", "invalid-input")
            self.fail("Reach did not throw a TypeError after getting invalid data input")
        except TypeError:
            pass

    def test_invalid_path(self):
        try:
            reach("dict.test", self.test_dict)
            self.fail("Reach did not throw a ValueError after getting path with invalid start")
        except ValueError:
            pass
        try:
            reach("$.", self.test_dict)
            self.fail("Reach did not throw a ValueError after getting invalid path")
        except ValueError:
            pass


class TestOverrideDict(TestCase):

    def setUp(self):
        self.parent = {
            "test": "test",
            "test1": "parent"
        }
        self.child = {
            "test1": "child",
            "test2": "child2"
        }

    def test_override_dict(self):
        new_dict = override_dict(self.parent, self.child)
        self.assertEqual(new_dict, {"test": "test", "test1": "child", "test2": "child2"})
        self.assertIsNot(new_dict, self.parent)
        new_dict = override_dict({}, self.child)
        self.assertEqual(new_dict, self.child)
        self.assertIsNot(new_dict, self.parent)
        new_dict = override_dict(self.parent, {})
        self.assertEqual(new_dict, self.parent)
        self.assertIsNot(new_dict, self.parent)

    def test_invalid_input(self):
        try:
            override_dict(self.parent, "child")
            self.fail("override_dict did not fail when receiving other type than dict as child")
        except AssertionError:
            pass
        try:
            override_dict(["parent"], self.child)
            self.fail("override_dict did not fail when receiving other type than dict as parent")
        except AssertionError:
            pass

    def test_override_dict_deep(self):
        self.parent["deep"] = {
            "constant": True,
            "variable": False
        }
        self.child["deep"] = {
            "variable": True
        }
        new_dict = override_dict(self.parent, self.child)
        self.assertEqual(new_dict, {
            "test": "test",
            "test1": "child",
            "test2": "child2",
            "deep": {
                # NB: deletes the constant key from parent!!
                "variable": True
            }
        })
        self.assertIsNot(new_dict, self.parent)


class TestIsJSONMimetype(TestCase):

    def test_is_json_mimetype(self):
        self.assertTrue(is_json_mimetype("application/json"))
        self.assertTrue(is_json_mimetype("application/vnd.api+json"))
        self.assertFalse(is_json_mimetype("application/pdf"))
        self.assertFalse(is_json_mimetype("text/html"))
