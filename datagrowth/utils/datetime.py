from datetime import datetime

from datagrowth.configuration import DATAGROWTH_CONFIGURATION


def parse_datetime_string(time_str):
    """
    Parses a time string to a datetime using the ``DATAGROWTH_DATETIME_FORMAT``.
    ``parse_datetime_string`` and ``format_datetime``
    consistently cast between strings and datetimes when used together.

    :param time_str: (str) a string representing a datetime
    :return: datetime
    """
    try:
        return datetime.strptime(time_str, DATAGROWTH_CONFIGURATION.DATETIME_FORMAT)
    except (ValueError, TypeError):
        return datetime(month=1, day=1, year=1970)


def format_datetime(datetime):
    """
    Formats a datetime into a string using the ``DATAGROWTH_DATETIME_FORMAT``
    ``parse_datetime_string`` and ``format_datetime``
    consistently cast between strings and datetimes when used together.

    :param datetime: a datetime object
    :return: string representing the datetime
    """
    return datetime.strftime(DATAGROWTH_CONFIGURATION.DATETIME_FORMAT)
