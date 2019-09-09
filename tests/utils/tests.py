from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch
from collections import Iterator
from tqdm import tqdm

from datagrowth.utils import parse_datetime_string, format_datetime, override_dict, ibatch


class TestDatetimeUtils(TestCase):

    def test_parse_datetime_string(self):
        birth_day_text = "19850501071059010"
        birth_day_obj = datetime(year=1985, month=5, day=1, hour=7, minute=10, second=59)
        beginning_of_time = datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0)
        parse = parse_datetime_string(birth_day_text)
        self.assertAlmostEqual(parse, birth_day_obj, delta=timedelta(seconds=1))
        birth_day_invalid = "01051985071059010"
        parse = parse_datetime_string(birth_day_invalid)
        self.assertEqual(parse, beginning_of_time)
        parse = parse_datetime_string(1534696182)
        self.assertEqual(parse, beginning_of_time)

    def test_format_datetime(self):
        birth_day_obj = datetime(year=1985, month=5, day=1, hour=7, minute=10, second=59)
        birth_day_text = format_datetime(birth_day_obj)
        self.assertEqual(birth_day_text, "19850501071059000000")
        try:
            format_datetime(1534696182)
            self.fail("format_datetime helper did not raise AttributeError when passing non-datetime")
        except AttributeError:
            pass


class TestIbatch(TestCase):

    def test_ibatch_with_list_no_progress(self):
        input = list(range(0, 100))
        # Neatly dividable batches
        iterator = ibatch(input, batch_size=20)
        self.assertIsInstance(iterator, Iterator)
        batches = [batch for batch in iterator]
        self.assertEqual(len(batches), 5)
        self.assertEqual(batches[0], list(range(0, 20)))
        self.assertEqual(batches[-1], list(range(80, 100)))
        # Rest batches
        iterator = ibatch(input, batch_size=11)
        self.assertIsInstance(iterator, Iterator)
        batches = [batch for batch in iterator]
        self.assertEqual(len(batches), 10)
        self.assertEqual(batches[0], list(range(0, 11)))
        self.assertEqual(batches[-1], list(range(99, 100)))

    def test_ibatch_with_iterator_no_progress(self):
        input = range(0, 100)
        # Neatly dividable batches
        iterator = ibatch(input, batch_size=20)
        self.assertIsInstance(iterator, Iterator)
        batches = [batch for batch in iterator]
        self.assertEqual(len(batches), 5)
        self.assertEqual(batches[0], list(range(0, 20)))
        self.assertEqual(batches[-1], list(range(80, 100)))
        # Rest batches
        iterator = ibatch(input, batch_size=11)
        self.assertIsInstance(iterator, Iterator)
        batches = [batch for batch in iterator]
        self.assertEqual(len(batches), 10)
        self.assertEqual(batches[0], list(range(0, 11)))
        self.assertEqual(batches[-1], list(range(99, 100)))

    def test_ibatch_with_list_progress_no_total(self):
        progress_bar_mock = Mock(spec=tqdm(disable=True))
        input = range(0, 100)
        with patch("datagrowth.utils.iterators.tqdm", return_value=progress_bar_mock) as tqdm_mock:
            # Neatly dividable batches
            iterator = ibatch(input, batch_size=20, progress_bar=True)
            self.assertIsInstance(iterator, Iterator)
            batches = [batch for batch in iterator]
            self.assertEqual(len(batches), 5)
            self.assertEqual(batches[0], list(range(0, 20)))
            self.assertEqual(batches[-1], list(range(80, 100)))
            tqdm_mock.assert_called_once_with()
            self.assertEqual(progress_bar_mock.update.call_count, 5)
            self.assertEqual(progress_bar_mock.close.call_count, 1)
        progress_bar_mock.reset_mock()
        with patch("datagrowth.utils.iterators.tqdm", return_value=progress_bar_mock) as tqdm_mock:
            # Rest batches
            iterator = ibatch(input, batch_size=11, progress_bar=True)
            self.assertIsInstance(iterator, Iterator)
            batches = [batch for batch in iterator]
            self.assertEqual(len(batches), 10)
            self.assertEqual(batches[0], list(range(0, 11)))
            self.assertEqual(batches[-1], list(range(99, 100)))
            tqdm_mock.assert_called_once_with()
            self.assertEqual(progress_bar_mock.update.call_count, 10)
            self.assertEqual(progress_bar_mock.close.call_count, 1)

    def test_ibatch_with_list_progress_and_total(self):
        input = range(0, 100)
        progress_bar_mock = Mock(spec=tqdm(disable=True))
        with patch("datagrowth.utils.iterators.tqdm", return_value=progress_bar_mock) as tqdm_mock:
            # Neatly dividable batches
            iterator = ibatch(input, batch_size=20, progress_bar=True, total=100)
            self.assertIsInstance(iterator, Iterator)
            batches = [batch for batch in iterator]
            self.assertEqual(len(batches), 5)
            self.assertEqual(batches[0], list(range(0, 20)))
            self.assertEqual(batches[-1], list(range(80, 100)))
            tqdm_mock.assert_called_once_with(total=5)
            self.assertEqual(progress_bar_mock.update.call_count, 5)
            self.assertEqual(progress_bar_mock.close.call_count, 1)
        progress_bar_mock.reset_mock()
        with patch("datagrowth.utils.iterators.tqdm", return_value=progress_bar_mock) as tqdm_mock:
            # Rest batches
            iterator = ibatch(input, batch_size=11, progress_bar=True, total=100)
            self.assertIsInstance(iterator, Iterator)
            batches = [batch for batch in iterator]
            self.assertEqual(len(batches), 10)
            self.assertEqual(batches[0], list(range(0, 11)))
            self.assertEqual(batches[-1], list(range(99, 100)))
            tqdm_mock.assert_called_once_with(total=10)
            self.assertEqual(progress_bar_mock.update.call_count, 10)
            self.assertEqual(progress_bar_mock.close.call_count, 1)


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
        new_dict = override_dict({}, self.child)
        self.assertEqual(new_dict, self.child)
        new_dict = override_dict(self.parent, {})
        self.assertEqual(new_dict, self.parent)

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
