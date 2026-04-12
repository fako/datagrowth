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
    pbar: tqdm | None = None
    if progress_bar:
        if not total:
            pbar = tqdm()
        else:
            batches = int(math.floor(total / batch_size))
            rest = total % batch_size
            if rest:
                batches += 1
            pbar = tqdm(total=batches)

    # The actual batch iterator
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            if pbar is not None:
                pbar.close()
            return
        if pbar is not None:
            pbar.update(1)
        yield batch
