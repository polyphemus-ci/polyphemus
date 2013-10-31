"""A simple class for distiguising between events coming from various sources.
"""

class Event(object):
    """A basic event class that has a kind (name, type, identifier, whatevs) and 
    some associated data.
    """

    def __init__(self, kind, data=None):
        """Parameters
        ----------
        kind : str
            The name of the event, such as 'github'. 
        data : optional
            Information associated with the even for the plugins to use.

        """
        self.kind = kind
        self.data = data

    def __str__(self):
        return "{0} event holding {1}".format(self.kind, self.data)

    def __repr__(self):
        return "{0}(kind={1}, data={2})".format(self.__class__.__name__, self.kind, 
                                                self.data)

    def __eq__(self, other):
        if not isinstance(other, Event):
            return NotImplemented
        return (self.name == other.name) and (self.data == other.data)
