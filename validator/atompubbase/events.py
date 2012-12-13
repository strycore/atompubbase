# Copyright Google 2007
"""
An eventing system for atompubbase objects.
Each class that is registered with add_event_handlers()
will be hooked into the event system. Clients can then
register for callbacks when a member function is called,
filtering on when to trigger the callback. There
are several axes that can be used to filter on:

Time          PRE|POST
Method Name   GET|PUT|DELETE|CREATE
Media         MEDIA|NEXT
Class         SERVICE|COLLECTION|ENTRY

Note that Class is really driven by which
classes use the eventing system. Media is triggered
if the method name ends in "_media".
For example, given the following class:

    class Entry(object):
        def get(self, headers, body = None):
            pass
        
        def put_media(self, headers, body = None):
            pass

It can be added to the event system by calling:
    
    add_event_handlers(Entry)

Now you can register callbacks for when methods of instances
of the class Entry are called. For example:

    def mycb(headers, body, attributes):
        pass

    register_callback("PRE_ENTRY", mycb)

The 'mycb' callback will be called before any
method is called in the Entry class. The headers
and body parameters will be passed along. The
headers can be changed by the callback.
You can construct a filter string by selecting zero
or one value across each axis and concatenating
them with underscores, order is not important.
PRE calls contain the header and body of the request,
POST calls contain the header and body of the response.
If you wish to receive all the events then register 
with the ANY filter.

Presuming registered classes:
  class Service:
      def get(headers, body=None): pass
  class Entry:
      def get(headers, body=None): pass
      def get_media(headers, body=None): pass
      def delete(headers, body=None): pass
      def put(headers, body): pass
      def put_media(headers, body): pass
  class Collection:
      def get(headers, body=None): pass
      def create(headers, body): pass

These are all valid filters:

    PRE_GET_MEDIA   - Called before Entry.get_media() is called
    PRE             - Called before any classes member function is called.
    COLLECTION      - Called before any Collection classes member function is called.
    POST_COLLECTION - Called after any Collection classes member function is called.
    POST_COLLECTION_CREATE - Called after Collection.create() is called.
    ANY             - Called before and after every classes member function is called.
"""
import sys

PREPOST = set(["PRE", "POST"])
WRAPPABLE = set(["get", "put", "delete", "create"])

class Events(object):
    def __init__(self):
        # Callbacks are a list of tuples (filter, cb)
        # where filter the set is the set of method attributes 
        # used to select that callback.
        self.callbacks = []
        
    def register(self, filter, cb):
        """
        Add a callback (cb) to be called when it matches
        the filter. The filter is a string of attibute 
        names separated by underscores.

        Example:
          events.register("PRE_ENTRY", mycb)

        The 'mycb' callback will be called before any
        method is called in the Entry class.
        """
        filter = set([coord for coord in filter.upper().split("_")])
        if not PREPOST.intersection(filter) and "ANY" not in filter:
            filter.add("PRE")
        self.callbacks.append((filter, cb))

    def clear(self):
        self.callbacks = []
        
    def trigger(self, when, methodname, instance, headers, body):
        method_filter = set(methodname.upper().split("_"))        
        method_filter.add(instance.__class__.__name__.upper())
        method_filter.add(when)
        matches = method_filter.copy()
        matches.add("ANY")
        for filter, cb in self.callbacks:
            if filter.issubset(matches):
                cb(headers, body, method_filter)
        

events = Events()


def _wrap(method, methodname):
    """
    Create a closure around the given method that calls into
    the eventing system.
    """
    def wrapped(self, headers=None, body=None):
        if headers == None:
          headers = {}
        try:
          headers["-request-uri"] = self.uri()
        except AttributeError:
          pass
        events.trigger("PRE", methodname, self, headers, body)
        (headers, body) = method(self, headers, body)
        events.trigger("POST", methodname, self, headers, body)
        return (headers, body)
    return wrapped

_wrapped = set()

def add_event_handlers(theclass):
    """
    Wrap each callable non-internal member function of the class
    with a wrapper function that calls into the eventing system.
    """
    if theclass not in _wrapped:
        for methodname in dir(theclass):
            method = getattr(theclass, methodname)
            methodprefix = methodname.split("_")[0]
            if methodprefix in WRAPPABLE and callable(method) and not methodname.startswith("_"):
                setattr(theclass, methodname, _wrap(method, methodname))
        _wrapped.add(theclass)

def register_callback(filter, cb):
    """
    Add a callback (cb) to be called when it matches
    the filter. The filter is a string of attibute 
    names separated by underscores.

    Example:
      register_callback("PRE_ENTRY", mycb)

    The 'mycb' callback will be called before any
    method is called in the Entry class.
    """
 
    events.register(filter, cb)

def clear():
    """
    Unregister all callbacks.
    """
    events.clear()


__all__ = ["add_event_handlers", "register_callback", "clear"]
