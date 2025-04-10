from typing import Any, Union, Callable

import re
import copy


JSON_MIMETYPE_PATTERN = re.compile("application/(.*)json")


def reach(path: Union[str, None], data: Any,
          default: any = None, default_factory: Union[Callable[[], Any], None] = None) -> Any:
    """
    Reach takes a path and data structure. It will return the value from the data structure belonging to the path.

    Paths are essentially multiple keys or indexes separated by ``.`` and start with ``$``.
    Each part of a path should correspond to another level in the structure given.

    Example data structure::

        {
            "test": {"test": "second level test"},
            "list of tests": ["test0","test1","test2"]
        }

    In the example above ``$.test.test`` as path would return "second level test"
    while ``$.test.1`` as path would return "test1".

    Reach will return None if path does not lead to a value in the data structure
    or the data structure entirely if path matches ``$``.

    :param path: (str) a key path starting with ``$`` to find in the data structure
    :param data: (dict, list or tuple) a data structure to search
    :param default: (any) default value to return if no value was found, defaults to None
    :param default_factory: (callable) factory for default value to return if no value was found
    :return: value corresponding to path in data structure or the default
    """

    if path == "$":
        return data
    elif path is not None and (not path.startswith("$.") or len(path) < 3):
        raise ValueError("Reach needs a path starting with $ followed by a dot and a key")
    elif path is not None:
        path = path[2:]

    # First we check whether we really get a structure we can use
    if path is None:
        return data
    if not isinstance(data, (dict, list, tuple)):
        raise TypeError(f"Reach needs dict, list or tuple as input, got {type(data)} instead")

    # Then we validate inputs for defaults
    if default is not None and default_factory is not None:
        raise ValueError("Reach can't compute a default value if default and default_factory are both specified.")
    if default_factory and not isinstance(default_factory, Callable):
        raise TypeError("Reach expects default_factory to be a Callable.")

    # We make a copy of the input for later reference
    root = copy.deepcopy(data)

    # We split the path and see how far we get with using it as key/index
    try:
        for part in path.split('.'):
            if part.isdigit():
                data = data[int(part)]
            else:
                data = data[part]
        else:
            return data

    except (IndexError, KeyError, TypeError):
        pass

    # We try the path as key/index or return the default.
    path = int(path) if path.isdigit() else path
    default_value = default_factory() if default_factory is not None else default
    return root[path] if path in root else default_value


def override_dict(parent, child):
    """
    A convenience function that will copy parent and then copy any items of child to that copy.

    :param parent: (dict) the source dictionary to use as a base
    :param child: (dict) a dictionary with items that should be added/overridden
    :return: a copy of parent with added/overridden items from child
    """
    assert isinstance(parent, dict), "The parent is not a dictionary."
    assert isinstance(child, dict), "The child is not a dictionary"
    return dict(parent.copy(), **child)


def is_json_mimetype(mimetype):
    return JSON_MIMETYPE_PATTERN.match(mimetype)
