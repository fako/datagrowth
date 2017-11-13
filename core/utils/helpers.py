from __future__ import unicode_literals, absolute_import, print_function, division

import operator
from datetime import datetime
from itertools import islice, cycle
from functools import reduce


from django.apps import apps as django_apps
from django.conf import settings


def get_any_model(name):
    try:
        app_label, model = next(
            (model._meta.app_label, model.__name__)
            for model in django_apps.get_models() if model.__name__ == name
        )
    except StopIteration:
        raise LookupError("Could not find {} in any app_labels".format(name))
    return django_apps.get_model(app_label, name)


def parse_datetime_string(time_str):
    try:
        return datetime.strptime(time_str, settings.DATASCOPE_DATETIME_FORMAT)
    except (ValueError, TypeError):
        return None


def format_datetime(datetime):
    return datetime.strftime(settings.DATASCOPE_DATETIME_FORMAT)


def override_dict(parent, child):
    assert isinstance(parent, dict), "The parent is not a dictionary."
    assert isinstance(child, dict), "The child is not a dictionary"
    return dict(parent.copy(), **child)


def merge_iter(*iterables, **kwargs):
    """
    Given a set of reversed sorted iterables, yield the next value in merged order
    Takes an optional `key` callable to compare values by.

    Based on: http://stackoverflow.com/questions/14465154/sorting-text-file-by-using-python/14465236#14465236
    """
    key_func = operator.itemgetter(0) if 'key' not in kwargs else lambda item, key=kwargs['key']: key(item[0])
    order_func = min if 'reversed' not in kwargs or not kwargs['reversed'] else max

    iterables = [iter(it) for it in iterables]
    iterables = {i: [next(it), i, it] for i, it in enumerate(iterables)}
    while True:
        value, i, it = order_func(iterables.values(), key=key_func)
        yield value
        try:
            iterables[i][0] = next(it)
        except StopIteration:
            del iterables[i]
            if not iterables:
                raise


def ibatch(iterable, batch_size):
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            return
        yield batch


def iroundrobin(*iterables):
    "iroundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))


def cross_combine(first, second):
    for primary in first:
        for secondary in second:
            yield (primary, secondary)


def cross_combine_2(*args):

    if len(args) == 1:
        return ((primary,) for primary in args[0])

    def dual_combine(first, second):
        for primary in first:
            for secondary in second:
                yield (primary, secondary)

    return reduce(dual_combine, args)
