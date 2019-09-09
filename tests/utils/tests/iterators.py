from unittest import TestCase
from unittest.mock import Mock, patch
from collections import Iterator
from tqdm import tqdm

from datagrowth.utils import ibatch


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
