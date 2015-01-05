"""
Extended JSON encoder for json

json.org do not specify how date time can be represented - monkeypatch it to do something.
"""

import datetime
import functools
import decimal
import json # is re-exported after monkey patching

__all__ = ['json']


def _is_tz_aware(value):
    """
    Determines if a given datetime.time is timezone aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return (value.tzinfo is not None
            and value.tzinfo.utcoffset(value) is not None)

def _obj_dump(obj):
    """
    Custom function for dumping objects to JSON, if obj has __json__ attribute
    or method defined it will be used for serialization

    :param obj:
    """

    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    # See "Date Time String Format" in the ECMA-262 specification.
    # some code borrowed from django 1.4
    elif isinstance(obj, datetime.datetime):
        r = obj.isoformat()
        if obj.microsecond:
            r = r[:23] + r[26:]
        if r.endswith('+00:00'):
            r = r[:-6] + 'Z'
        return r
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return str(obj)
    elif isinstance(obj, datetime.time):
        if _is_tz_aware(obj):
            raise ValueError("JSON can't represent timezone-aware times.")
        r = obj.isoformat()
        if obj.microsecond:
            r = r[:12]
        return r
    elif isinstance(obj, set):
        return list(obj)
    elif hasattr(obj, '__json__'):
        if callable(obj.__json__):
            return obj.__json__()
        else:
            return obj.__json__
    else:
        raise NotImplementedError


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return _obj_dump(obj)
        except NotImplementedError:
            pass
        raise TypeError("%r is not JSON serializable" % (obj,))


# monkey-patch and export JSON encoder to use custom encoding method
json.dumps = functools.partial(json.dumps, cls=ExtendedEncoder)
json.dump = functools.partial(json.dump, cls=ExtendedEncoder)
