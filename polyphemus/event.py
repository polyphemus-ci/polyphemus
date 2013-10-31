"""A simple class for distiguising between events coming from various sources.
"""
from functools import wraps

class Event(object):
    """A basic event class that has a kind (name, type, identifier, whatevs) and 
    some associated data.
    """

    def __init__(self, name, data=None):
        """Parameters
        ----------
        name : str
            The kind of the event, such as 'github'. 
        data : optional
            Information associated with the even for the plugins to use.

        """
        self.name = name
        self.data = data

    def __str__(self):
        return "{0} event holding {1}".format(self.name, self.data)

    def __repr__(self):
        return "{0}(kind={1}, data={2})".format(self.__class__.__name__, self.name, 
                                                self.data)

    def __eq__(self, other):
        if not isinstance(other, Event):
            return NotImplemented
        return (self.name == other.name) and (self.data == other.data)

def runfor(*events):
    """A decorator for running only certain events.
    """
    events = frozenset(events)
    def dec(f):
        @wraps(f)
        def wrapper(self, rc, *args, **kwargs):
            if rc.event.name not in events:
                return 
            return f(self, rc, *args, **kwargs)
        return wrapper
    return dec
