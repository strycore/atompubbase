"""
There are four classes that make up the core
of the atompub model.

class Context
class Service
class Collection
class Entry

Context represents the current state, as represented
by a service document, a collection and an entry.

Each atompub object (Service, Collection, or Entry) 
is just instantiated with a URI (or with a Context)
that it then uses to perform its work. Each object can produce
a list of URIs (actually Context objects) (possibly filtered) 
for the next level down. The only parsing done will be xpaths to
pick out URIs, e.g. collections from service documents. 
Here is an example of how the classes are used together:

    # Note that httplib2.Http is passed in so you 
    # can pass in your own instrumented version, etc.
    from httplib2 import Http
    h = httplib2.Http()
    c = Context(h, service_document_uri)
    service = Service(c)

    collection = Collection(service.iter()[0]) 
    entry = Entry(collection.iter()[0])
    (headers, body) = entry.get()
    body = "<entry>...some updated stuff </entry>"
    entry.put(body)

    # saving and restoring is a matter of pickling/unpickling the Context.
    import pickle
    f = file("somefile", "w")
    pickle.dump(entry.context(), f)

    import pickle
    f = file("somefile", "r")
    context = pickle.load(f)
    # You pass the class names into restore() for it to use to restore the context.
    (service, collection, entry) = context.restore(Service, Collection, Entry)

    # You don't have to use the context, Entries
    # and Collections can be instantiated from URIs instead
    # of Context instances.
    entry = Entry(entry_edit_uri)

"""
import events
from mimeparse import mimeparse
import urlparse
import httplib2
import copy

try:
    from xml.etree.ElementTree import fromstring, tostring
except:
    from elementtree.ElementTree import fromstring, tostring

from xml.parsers.expat import ExpatError

ATOM = "http://www.w3.org/2005/Atom"
XHTML = "http://www.w3.org/1999/xhtml"
APP = "http://www.w3.org/2007/app"

ATOM_ENTRY = "{%s}entry" % ATOM
LINK = "{%s}link" % ATOM
ATOM_TITLE= "{%s}title" % ATOM
APP_COLL = "{%s}collection" % APP
APP_MEMBER_TYPE = "{%s}accept" % APP
XHTML_DIV = "{%s}div" % XHTML

class ParseException(Exception):
    def __init__(self, headers, body):
        self.headers = headers
        self.body = body
    def __str__(self):
        return "XML is non-well-formed"

def get_child_title(node):
    title = node.find(".//" + ATOM_TITLE)
    if title == None:
        return ""
    title_type = title.get('type', 'text')
    if title_type in ['text', 'html']:
        return title.text
    else:
        div = title.find(".//" + XHTML_DIV)
        div_text = div.text + "".join([c.text + c.tail for c in div.getchildren()])
        return div_text


def absolutize(baseuri, uri):
    """
    Given a baseuri, return the absolute
    version of the given uri. Works whether
    uri is relative or absolute.
    """
    if uri == None:
        return None
    (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
    if not authority:
        uri = urlparse.urljoin(baseuri, uri)
    return uri

def link_value(etree, xpath, relation):
    """
    Given and elementtree element 'etree', find all link
    elements under the given xpath and return the @href
    of the link of the given relation.
    """
    xpath = xpath + "/" + LINK 
    for link in etree.findall(xpath):
        if link.get('rel') == relation:
            return link.get('href')
    return None


class Context(object):
    """
    Encapsulates the current service documents,
    the current collection and the current 
    entry. Can be picked and un-pickled to
    achieve persistence of context.
    """
    _service = None
    _collection = None 
    _entry = None
    http = None
    _collection_stack = []

    def __init__(self, http = None, service=None, collection=None, entry=None):
        """http is either an instance of httplib2.Http() or something that 
        acts like it. For this module the only tow functions that need to 
        be implemented are request() and add_credentials().
        """
        self._collection_stack = []
        if http:
            self.http = http
        else:
            self.http = httplib2.Http()
        self._service = service
        self._collection = collection
        self._entry = entry

    def _get_service(self):
        return self._service

    def _set_service(self, service):
        self._service = service
        self._collection = None 
        self._collection_stack = [] 
        self._entry = None 

    service = property(_get_service, _set_service, None, "The URI of the Service Document. None if not set yet.")

    def _get_collection(self):
        return self._collection

    def _set_collection(self, collection):
        self._collection = collection
        self._collection_stack = []
        self._entry = None 

    collection = property(_get_collection, _set_collection, None, "The URI of the collection. None if not set yet.")

    def _get_entry(self):
        return self._entry

    def _set_entry(self, entry):
        self._entry = entry

    entry = property(_get_entry, _set_entry, None, "The URI of the entry. None if not set yet.")

    def restore(self, service_type, collection_type, entry_type):
        """
        Restore the state from a Context. The types of the objects
        to be instantiated for the service, collection and entry 
        are passed in. If no URI is set for a specific level 
        then None is returned for that instance.
        """
        service = self._service and service_type(self) or None
        collection = self._collection and collection_type(self) or None
        entry = self._entry and entry_type(self) or None
        return (service, collection, entry)

    def collpush(self, uri):
        """
        The collpush and collpop members are similar to the
        command line 'pushd' and 'popd' commands. They let you
        change to a different collection and then pop back
        to the older collection when you are done.
        """
        self._collection_stack.append((self._collection, self._entry))
        self._collection = uri
        self._entry = None 

    def collpop(self):
        """
        See collpush.
        """
        self._collection, self._entry = self._collection_stack.pop()

    

class Service(object):
    """
    An Atom Publishing Protocol Service Document.
    """
    def __init__(self, context_or_uri):
        self.context = isinstance(context_or_uri, Context) and context_or_uri or Context(service=context_or_uri) 
        self.representation = None
        self._etree = None

    def context(self):
        """
        Get the curent Context associated with this Service Document.
        """
        return self.context

    def uri(self):
        return self.context.service

    def get(self, headers=None, body=None):
        """
        Retrieve the current Service Document from the server.

        Returns a tuple of the HTTP response headers
        and the body.
        """
        headers, body = self.context.http.request(self.context.service, headers=headers)
        if headers.status == 200:
            self.representation = body
            try:
                self._etree = fromstring(body)
            except ExpatError:
                raise ParseException(headers, body)
        return (headers, body)

    def etree(self):
        """
        Returns an ElementTree representation of the Service Document.
        """
        if not self._etree:
            self.get()
        return self._etree

    def iter_match(self, mimerange):
        """
        Returns a generator that iterates over 
        the collections in the service document 
        that accept the given mimerange. The mimerange
        can be a specific mimetype - "image/png" - or 
        a range - "image/*". 
        """
        if not self.representation:
            headers, body = self.get()
        for coll in self._etree.findall(".//" + APP_COLL):
            accept_type = [t.text for t in coll.findall(APP_MEMBER_TYPE)] 
            if len(accept_type) == 0:
                accept_type.append("application/atom+xml")
            coll_type = [t for t in accept_type if mimeparse.best_match([t], mimerange)] 
            if coll_type:
                context = copy.copy(self.context)
                context.collection = absolutize(self.context.service, coll.get('href')) 
                yield context

    def iter(self):
        """
        Returns a generator that iterates over all
        the collections in the service document.
        """
        return self.iter_match("*/*")

    def iter_info(self):
        """
        Returns a generator that iterates over all
        the collections in the service document.
        Each yield tuple contains the collection
        URI, the collection title and the workspace title
        """
        if not self.representation:
            headers, body = self.get()
        for workspace in self._etree.findall(".//{%s}workspace" % APP):
            workspace_title = get_child_title(workspace)
            for coll in workspace.findall(".//" + APP_COLL):
                coll_title = get_child_title(coll)
                coll_uri = absolutize(self.context.service, coll.get('href'))
                yield (workspace_title, coll_title, coll_uri)


class Collection(object):
    def __init__(self, context_or_uri):
        """
        Create a Collection from either the URI of the
        collection, or from a Context object.
        """
        self._context = isinstance(context_or_uri, Context) and context_or_uri or Context(service=context_or_uri) 
        self.representation = None
        self._etree = None
        self.next = None

    def context(self):
        """
        The Context associated with this Collection.
        """
        return self._context

    def uri(self):
        return self._context.collection

    def etree(self):
        """
        Returns an ElementTree representation of the 
        current page of the collection.
        """
        if not self.representation:
            self.get()
        return self._etree

    def _record_next(self, base_uri, headers, body):
        if headers.status == 200:
            self.representation = body
            try:
                self._etree = fromstring(body)
            except ExpatError:
                raise ParseException(headers, body)
            self.next = link_value(self._etree, ".", "next")
            if self.next:
                self.next = absolutize(base_uri, self.next) 
        else:
            self.representation = self._etree = selfnext = None

    def get(self, headers=None, body=None):
        """
        Retrieves the first feed in a paged series of 
        collection documents.

        Returns a tuple of the HTTP response headers
        and the body.
        """
        headers, body = self._context.http.request(self._context.collection, headers=headers, body=body)
        self._record_next(self._context.collection, headers, body)
        return (headers, body)

    def has_next(self):
        """
        Collections can be paged across many
        Atom feeds. Returns True if there is a 
        'next' feed we can get.
        """
        return self.next != None

    def get_next(self, headers=None, body=None):
        """
        Collections can be paged across many
        Atom feeds. Get's the next feed in the
        paging.

        Returns a tuple of the HTTP response headers
        and the body.
        """
        headers, body = self._context.http.request(self.next, headers=headers, body=body)
        self._record_next(self.next, headers, body)
        return (headers, body)

    def create(self, headers=None, body=None):
        """
        Create a new member in the collection.
        Can be used to create members of regular
        and media collections. Be sure to set the 
        'content-type' header appropriately.

        Returns a tuple of the HTTP response headers
        and the body.
        """
        headers, body = self._context.http.request(self._context.collection, method="POST", headers=headers, body=body)
        return (headers, body)

    def entry_create(self, headers=None, body=None):
        """
        Convenience method that returns an Entry object
        if the create has succeeded, or None if it fails.
        """
        headers, body = self._context.http.request(self._context.collection, method="POST", headers=headers, body=body)
        if headers.status == 201 and 'location' in headers:
            context = copy.copy(self._context)
            context.entry = headers['location']
            return context
        else:
            return None

    def iter(self):
        """
        Returns in iterable that produces a Context 
        object for every Entry in the collection.
        """
        self.get()
        while True:
            for entry in self._etree.findall(ATOM_ENTRY):
                context = copy.copy(self._context)
                edit_link = link_value(entry, ".", "edit")
                context.entry = absolutize(self._context.collection, edit_link) 
                yield context
            if self.has_next():
                self.get_next()
            else:
                break

    def iter_entry(self):
        """
        Returns in iterable that produces an elementtree
        Entry for every Entry in the collection. Note that this
        Entry is the possibly incomplete Entry in the collection
        feed.
        """
        self.get()
        while True:
            for entry in self._etree.findall(ATOM_ENTRY):
                yield entry
            if self.has_next():
                self.get_next()
            else:
                break





class Entry(object):
    def __init__(self, context_or_uri):
        """
        Create an Entry from either the URI of the
        entry edit URI, or from a Context object.
        """
        self._context = isinstance(context_or_uri, Context) and context_or_uri or Context(entry=context_or_uri) 
        self.representation = None
        self._etree = None
        self.edit_media = None

    def _clear(self):
        self.representation = None
        self._etree = None
        self.edit_media = None

    def etree(self):
        """
        Returns an ElementTree representation of the Entry.
        """
        if not self.representation:
            self.get()
        return self._etree

    def context(self):
        return self._context

    def uri(self):
        return self._context.entry


    def get(self, headers=None, body=None):
        """
        Retrieve the representation for this entry.
        """
        headers, body = self._context.http.request(self._context.entry, headers=headers)
        self.representation = body

        try:
            self._etree = fromstring(body)
        except ExpatError:
            raise ParseException(headers, body)
        

        self.edit_media = absolutize(self._context.entry, link_value(self._etree, ".", "edit-media")) 

        return (headers, body)

    def has_media(self):
        """
        Returns True if this is a Media Link Entry.
        """
        if not self.representation:
            self.get()
        return self.edit_media != None

    def get_media(self, headers=None, body=None):
        """
        If this entry is a Media Link Entry, then retrieve
        the associated media.
        """
        if not self.representation:
            self.get()
        headers, body = self._context.http.request(self.edit_media, headers=headers)
        return (headers, body)

    def put(self, headers=None, body=None):
        """
        Update the entry on the server. If the body to send
        is not supplied then the internal elementtree element
        will be serialized and sent to the server.
        """
        if headers == None:
            headers = {}
        if 'content-type' not in headers:
            headers['content-type'] = 'application/atom+xml;type=entry'
        if not self.representation:
            self.get()
        if body == None:
            body = tostring(self._etree)
        headers, body = self._context.http.request(self._context.entry, headers=headers, method="PUT", body=body)
        if headers.status < 300:
            self._clear()
        return (headers, body)

    def put_media(self, headers=None, body=None):
        """
        If this entry is a Media Link Entry, then update 
        the associated media.
        """
        if not self.representation:
            self.get()
        headers, body = self._context.http.request(self.edit_media, headers=headers, method="PUT", body=body)
        if headers.status < 300:
            self._clear()
        return (headers, body)

    def delete(self, headers=None, body=None):
        """
        Delete the entry from the server.
        """
        headers, body = self._context.http.request(self._context.entry, headers=headers, method="DELETE")
        if headers.status < 300:
            self._clear()
        return (headers, body)


def init_event_handlers():
    """
    Add in hooks to the Service, Collection
    and Entry classes to enable Events.
    """
    events.add_event_handlers(Service)
    events.add_event_handlers(Collection)
    events.add_event_handlers(Entry)
