import math
from itertools import islice
from tqdm import tqdm


def ibatch(iterable, batch_size, progress_bar=False, total=None):
    """
    Creates an iterator that iterates over an iterable in batches of a constant size.
    Each batch will be held in memory.
    Optionally this function will display a progress bar, showing the amount of iterated batches.

    :param iterable: (iter) the iterator to batchify
    :param batch_size: (int) the size of one batch
    :param progress_bar: (bool) whether to display a progress bar
    :param total: (int) the size of the iterator (only used for the progress bar)
    :return: Iterator
    """
    progress_bar = progress_bar or None

    # Setup a progress bar if requested
    if progress_bar and not total:
        progress_bar = tqdm()
    elif progress_bar and total:
        batches = int(math.floor(total / batch_size))
        rest = total % batch_size
        if rest:
            batches += 1
        progress_bar = tqdm(total=batches)

    # The actual batch iterator
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            if progress_bar is not None:
                progress_bar.close()
            return
        if progress_bar is not None:
            progress_bar.update(1)
        yield batch
