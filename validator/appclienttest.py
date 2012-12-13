__author__ = "Joe Gregorio <http://bitworking.org/>"
__version__ = "$Revision: 150 $"
__copyright__ = "Copyright (c) 2006 Joe Gregorio"
__license__ = "MIT"

import os 
import sys
import httplib2
try:
      from xml.etree.ElementTree import fromstring, tostring, SubElement
except:
      from elementtree.ElementTree import fromstring, tostring, SubElement

import atompubbase
import atompubbase.auth
from atompubbase.model import Entry, Collection, Service, Context, init_event_handlers, ParseException
import urlparse
import cStringIO
import sys
from optparse import OptionParser
import time
import feedvalidator
from feedvalidator import compatibility
from mimeparse import mimeparse
from xml.sax.saxutils import escape
from feedvalidator.formatter.text_plain import Formatter as text_formatter

import xml.dom.minidom
import random
import base64
import urllib
import re
import copy

# By default we'll check the bitworking collection 
INTROSPECTION_URI = "http://bitworking.org/projects/apptestsite/app.cgi/service/;service_document"

parser = OptionParser()
parser.add_option("--credentials", dest="credentials",
                    help="FILE that contains a name and password on separate lines with an optional third line with the authentication type of 'ClientLogin <service>'.",
                    metavar="FILE")
parser.add_option("--output", dest="output",
                    help="FILE to store test results",
                    metavar="FILE")
parser.add_option("--verbose",
                  action="store_true", 
                  dest="verbose",
                  default=False,
                  help="Print extra information while running.")
parser.add_option("--quiet",
                  action="store_true", 
                  dest="quiet",
                  default=False,
                  help="Do not print anything while running.")
parser.add_option("--debug",
                  action="store_true", 
                  dest="debug",
                  default=False,
                  help="Print low level HTTP information while running.")
parser.add_option("--html",
                  action="store_true", 
                  dest="html",
                  default=False,
                  help="Output is formatted in HTML")
parser.add_option("--record",
                  dest="record",
                  metavar="DIR",
                  help="Record all the responses to be used later in playback mode.")
parser.add_option("--playback",
                  dest="playback",
                  metavar="DIR",
                  help="Playback responses stored from a previous run.")


options, cmd_line_args = parser.parse_args() 


# Restructure so that we use atompubbase
# Add hooks that do validation of the documents at every step
# Add hooks to specific actions that validate other things (such as response status codes)
# Add hooks that log the requests and responses for later inspection (putting them on the HTML page).
#
# Need an object to keep track of the current state, i.e. the test and
# request/response pair that each error/warning/informational is about.
#
# Need to track the desired output format.
#
# Might have to fix up the anchors that the html formatter produces.
#
# Create an httplib2 instance for atompubbase that has a memory based cache.

atompubbase.model.init_event_handlers()


def get_test_data(filename):
  return unicode(file(os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   filename), "r").read(), "utf-8")

def get_test_data_raw(filename):
  return file(os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   filename), "r").read()

def method_from_filters(filters):
  method = "GET"
  if "CREATE" in filters:
    method = "POST"
  elif "PUT" in filters:
    method = "PUT"
  elif "DELETE" in filters:
    method = "DELETE"
  return method

class MemoryCache:
  mem = {}

  def set(self, key, value):
    self.mem[key] = value

  def get(self, key):
    return self.mem.get(key, None)

  def delete(self, key):
    if key in self.mem:
      del self.mem[key]


class Enum:
  def __init__(self, **entries):
    self.entries = entries
    self.order = entries.keys()
    self.__dict__.update([(name, i) for (i, name) in enumerate(entries.keys())])

  def name(self, index):
    return self.order[index]

  def desc(self, index):
    return self.entries[self.name(index)]


# Make this an enum
msg = Enum(
  VALID_ATOM = "[RFC4287]",
  ENTRIES_ORDERED_BY_ATOM_EDITED = "[RFC5023] Section 10",
  CREATE_RETURNS_201 = "[RFC5023] Section 9.2",
  CREATE_RETURNS_LOCATION = "[RFC5023] Section 9.2",
  CREATE_CONTENT_LOCATION = "[RFC5023] Section 9.2",  
  CREATE_RETURNS_ENTRY = "[RFC5023] Section 9.2",
  CREATE_APPEAR_COLLECTION = "[RFC5023] Section 9.1",
  PUT_STATUS_CODE = "[RFC2616] Section 9.6",
  GET_STATUS_CODE = "[RFC2616] Section 10.2.1",
  DELETE_STATUS_CODE = "[RFC2616] Section 9.7",
  SLUG_HEADER = "[RFC5023] Section 9.7",
  ENTRY_LINK_EDIT = "[RFC5023] Section 9.1",
  MEDIA_ENTRY_LINK_EDIT = "[RFC5023] Section 9.6",
  HTTP_ETAG = "[RFC2616] Section 13.3.4",
  HTTP_LAST_MODIFIED = "[RFC2616] Section 13.3.4",  
  HTTP_CONTENT_ENCODING = "[RFC2616] Section 14.11",  
  WELL_FORMED_XML = "[W3C XML 1.0] Section 2.1 sec-well-formed",
  INTERNATIONALIZATION = "[W3C XML 1.0] Section 2.1 charsets",  
  CRED_FILE = "[AppClietTest]",
  INFO = "Info",
  SUCCESS = "",
  REQUEST = "Request",
  RESPONSE = "Response",
  BEGIN_TEST = ""
)

class StopTest(Exception):
  "Exception to raise if you want to stop the current test."
  pass

RFC = re.compile("\[RFC(?P<number>\d{4})\] Section (?P<section>\S+)$")
RFC_URI = "http://tools.ietf.org/html/rfc%(number)s#section-%(section)s"
W3C = re.compile("\[W3C XML 1.0\] Section (\S+) (?P<section>\S+)$")
W3C_URI = "http://www.w3.org/TR/REC-xml/#%(section)s"

def expand_spec_reference(message):
  html_message = ' '
  if message != msg.INFO:
    html_message = msg.desc(message)
  match = RFC.search(html_message)
  if match:
    uri = RFC_URI % match.groupdict()
    html_message = "<a href='%s'>%s</a>" % (uri, html_message)
  match = W3C.search(html_message)
  if match:
    uri = W3C_URI % match.groupdict()
    html_message = "<a href='%s'>%s</a>" % (uri, html_message)
  return html_message  

class Recorder:
  """
  Records all the warning, errors, etc. and is able to
  spit the results out as a text or html report.
  """
  transcript = [] # a list of (MSG_TYPE, message, details)
  tests = []
  html = False
  verbosity = 0
  has_errors = False
  has_warnings = False

  def __init__(self):
    atompubbase.events.register_callback("ANY", self.log_request_response)
    atompubbase.events.register_callback("POST_CREATE", self.create_validation_cb)
    atompubbase.events.register_callback("POST_GET", self.get_check_response_cb)
    atompubbase.events.register_callback("POST_GET", self.content_validation_cb)


  def error(self, message, detail):
    self.has_errors = True
    self.transcript.append(("Error", message, detail))

  def warning(self, message, detail):
    self.has_warnings = True    
    self.transcript.append(("Warning", message, detail))

  def info(self, detail):
    self.transcript.append(("Info", msg.INFO, detail))

  def success(self, detail):
    self.transcript.append(("Success", msg.SUCCESS, detail))

  def log(self, message, detail):
    self.transcript.append(("Log", message, detail))

  def _end_test(self):
    if self.transcript:
      self.tests.append(self.transcript)
      self.transcript = []

  def begin_test(self, detail):
    self._end_test()
    self.transcript.append(("Begin_Test", msg.BEGIN_TEST, detail))

  def tostr(self):
    self._end_test()
    if self.html:
      return self._tohtml()
    else:
      return self._totext()

  def _tohtml(self):
    resp = [u"""<!DOCTYPE HTML>
<html>
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8">
    <link href="validator/res/base.css" type="text/css" rel="stylesheet">
    <script type="text/javascript" src="validator/res/jquery-1.2.3.js"></script>
    <script type="text/javascript" src="validator/res/report.js" ></script>
    <link href="validator/res/prettify.css" type="text/css" rel="stylesheet" />
    <script type="text/javascript" src="validator/res/prettify.js"></script>
    <title>AppClientTest - Results</title>
  </head>
<body>
  <h1>Test Report</h1>
  <dl>
    <dt>Date</dt>
    <dd>%s</dd>
  </dl>
  <div class='legend'>
  <h3>Legend</h3>
  <dl>
     <dt><img src='validator/res/info.gif'> Informational</dt>
     <dd>Information on what was being tested.</dd>
     <dt><img src='validator/res/warning.gif'> Warning</dt>
     <dd>Warnings indicate behavior that, while legal, may cause<br/>
       either performance or interoperability problems in the field.</dd>
     <dt><img src='validator/res/error.gif'> Error</dt>
     <dd>Errors are violations of either the Atom, AtomPub<br/> or HTTP specifications.</dd>
     <dt><img src='validator/res/log.gif'> Log</dt>
     <dd>Detailed information on the transaction to help you<br/> debug your service.</dd>
     <dt><img src='validator/res/success.gif'> Success</dt>
     <dd>A specific sub-test has been passed successfully.</dd>
     
  </div>
  """ % (time.asctime())] 
    for transcript in self.tests:
      (code, message, detail) = transcript[0]
      transcript = transcript[1:]
      resp.append(u"<h2>%s</h2><p>%s</p>\n" % tuple(detail.split(":")))
      resp.append(u"<ol>\n")
      # convert msg.desc(message) into a link if possible
      resp.extend([u"  <li class='%s'><img src='validator/res/%s.gif'> %s <span class='%s'>%s</span></li>\n" %
                   (code, code.lower(), expand_spec_reference(message), code, detail) for (code, message, detail) in transcript])
      resp.append(u"</ol>\n")
    return (u"".join(resp)).encode("utf-8")

  def _totext(self):
    resp = []
    for transcript in self.tests:
      resp.extend([u"%s:%s %s" % (code, msg.name(message), detail) for (code, message, detail) in transcript if code not in ["Log", "Info"]])
    return (u"\n".join(resp)).encode("utf-8")

  def _validate(self, headers, body):
    if headers.status in [200, 201]:
      baseuri = headers.get('content-location', '')
      try:
          events = feedvalidator.validateStream(cStringIO.StringIO(body),
                                                firstOccurrenceOnly=1,
                                                base=baseuri)['loggedEvents']
      except feedvalidator.logging.ValidationFailure, vf:
          events = [vf.event]

      errors = [event for event in events if isinstance(event, feedvalidator.logging.Error)]
      if errors:
        self.error(msg.VALID_ATOM, "\n".join(text_formatter(errors)))

      warnings = [event for event in events if isinstance(event, feedvalidator.logging.Warning)]
      if warnings:
        self.warning(msg.VALID_ATOM, "\n".join(text_formatter(warnings)))

      if self.verbosity > 2:
        infos = [event for event in events if isinstance(event, feedvalidator.logging.Info)]
        if infos:
          self.info("\n".join(text_formatter(infos)))

  def content_validation_cb(self, headers, body, filters):
    self._validate(headers, body)

  def create_validation_cb(self, headers, body, filters):
    self._validate(headers, body)

  def get_check_response_cb(self, headers, body, filters):
    """
    For operations that should return 200, like get, put and delete.
    """
    if headers.status != 200:
      error(msg.GET_STATUS_CODE, "Could not successfully retrieve the document. Got a status code of: %d" % headers.status)
      raise StopTest
    if not headers.has_key('etag'):
      self.warning(msg.HTTP_ETAG, "No ETag: header was sent with the response.")
      if not headers.has_key('last-modified'):
        self.warning(msg.HTTP_LAST_MODIFIED, "No Last-Modified: header was sent with the response.")
    if headers.get('content-length', 0) > 0 and not headers.has_key('-content-encoding'):
      self.warning(msg.HTTP_CONTENT_ENCODING, "No Content-Encoding: header was sent with the response indicating that a compressed entity body was not returned.")

  def log_request_response(self, headers, body, filters):
    request_line = u""
    if "PRE" in filters:
      direction = msg.REQUEST
      if "-request-uri" in headers:
        uri = headers["-request-uri"]
        del headers["-request-uri"]
        method = method_from_filters(filters)
        request_line = method + u" " + uri
    else:
      direction = msg.RESPONSE
    headers_str = request_line + "\n" + u"\n".join(["%s: %s" % (k, v) for (k, v) in headers.iteritems()])
    need_escape = True
    if body == None or len(body) == 0:
      body = u""
    else:
      if 'content-type' in headers:
        mtype, subtype, params = mimeparse.parse_mime_type(headers['content-type'])
        if subtype[-4:] == "+xml":
          try:
            dom = xml.dom.minidom.parseString(body)
            body = dom.toxml()
            if len(body.splitlines()) < 2:
              body = dom.toprettyxml()            
          except xml.parsers.expat.ExpatError:
            try:
              body = unicode(body, params.get('charset', 'utf-8'))
            except UnicodeDecodeError:
              try:
                body = unicode(body, 'iso-8859-1')
              except UnicodeDecodeError:
                body = urllib.quote(body)
        elif 'charset' in params:
          body = unicode(body, params['charset'])
        elif mtype == 'image' and self.html:
          body = "<img src='data:%s/%s;base64,%s'/>" % (mtype, subtype, base64.b64encode(body))
          need_escape = False
        else:          
          body = "Could not safely serialize the body"          
      else:
        body = "Could not safely serialize the body"

    if headers_str or body or request_line:
      if self.html and need_escape:
        body = escape(body)
      if self.html:
        log = u"<pre><code>\n" + escape(headers_str) + "\n\n\n</code></pre>\n<pre><code class='prettyprint'>" + body + u"</code></pre>"
      else:
        log = headers_str + "\n\n" + body
      self.log(direction, log)


recorder = Recorder()
error    = recorder.error
warning  = recorder.warning
info     = recorder.info
success  = recorder.success
begin_test = recorder.begin_test


class Test:
    """Base class for all the tests. Has a 'run' member
    function which runs over all member functions
    that begin with 'test' and executes them.
    """
    def __init__(self):
        self.reports = []
        self.context = ""
        self.collection_uri = ""
        self.entry_uri = ""

    def run(self):
        methods = [ method for method in dir(self) if callable(getattr(self, method)) and method.startswith("test")]
        for method in methods:
            if not options.quiet:
              print >>sys.stderr, ".",
            sys.stdout.flush()
            test_member_function = getattr(self, method)
            try:
                self.description = str(test_member_function.__doc__)
                self.context = method
                begin_test(method.split("test", 1)[1].replace("_", " ") + ":" + self.description)
                test_member_function()
            except StopTest:
                pass
            except ParseException, e:
                recorder.log_request_response(e.headers, e.body, set(["POST"]))
                error(msg.WELL_FORMED_XML, "Not well-formed XML")
            except Exception, e:
                import traceback
                info("Internal error occured while running tests: " + str(e) + traceback.format_exc())


def check_order_of_entries(entries, order):
  info("Check order of entries in the collection document")
  failed = False
  for e in entries:
    idelement = e.find("{%s}id" % atompubbase.model.ATOM)
    if None != idelement and idelement.text in order:
      if order[0] != idelement.text:
        error(msg.ENTRIES_ORDERED_BY_ATOM_EDITED, "Failed to preserve order of entries, was expecting %s, but found %s" % (order[0], idelement.text))
        failed = True
        break
      else:
        order = order[1:]
    if len(order) == 0:
      break
  if len(order) and not failed:
    warning(msg.CREATE_APPEAR_COLLECTION, "All entries did not appear in the collection. The following ids never appeared: %s" % str(order))
    failed = True
  if not failed:
    success("Order of entries is correct")

def check_create_response(h, b):
  if h.status != 201:
    error(msg.CREATE_RETURNS_201, "Entry creation failed with status: %d %s" % (h.status, h.reason))
    raise StopTest
  if 'location' not in h:
    error(msg.CREATE_RETURNS_LOCATION, "Location: not returned in response headers.")
    raise StopTest    
  if 'content-location' not in h:
    warning(msg.CREATE_CONTENT_LOCATION, "Content-Location: not returned in response headers.")
  if len(b) == 0:
    warning(msg.CREATE_RETURNS_ENTRY, "Atom Entry not returned on member creation.")

def check_entry_slug(e, slug):
    slugified = [link for link in e.findall("{%s}link" % atompubbase.model.ATOM)
                   if ('rel' not in link.attrib or link.attrib['rel'] == "alternate") and slug in link.attrib['href']]
    if not slugified:
      warning(msg.SLUG_HEADER, "Slug was ignored")
    else:
      success("Slug was honored")

def check_entry_links(e, ismedia):
    editlink = [link for link in e.findall("{%s}link" % atompubbase.model.ATOM)
                 if ("edit" == link.attrib.get('rel', None))]
    if not editlink:
      warning(msg.ENTRY_LINK_EDIT, "Member Entry did not contain an atom:link element with a relation of 'edit'")
    else:
      success("Member contained an 'edit' link")

    if ismedia:
        editmedialink = [link for link in e.findall("{%s}link" % atompubbase.model.ATOM)
                       if ("edit-media" == link.attrib.get('rel', None))]
        if not editmedialink:
          warning(msg.MEDIA_ENTRY_LINK_EDIT, "Member Entry did not contain an atom:link element with a relation of 'edit-media'")
        else:
          success("Member contained an 'edit-media' link")
          
def check_update_response(h, b, desc):
    if h.status not in [200, 204]:
      error(msg.PUT_STATUS_CODE, "Failed to accept updated %s" % desc)
    else:
      success("Updated %s" % desc)

def check_remove_response(h, b):
    if h.status not in [200, 202, 204]:
        error(msg.DELETE_STATUS_CODE, "Entry removal failed with status: %d %s" % (h.status, h.reason))
        raise StopTest

def get_entry_id(context, h, b):
  entry_id = None
  if 'location' in h:
    entry_context = copy.copy(context)
    entry_context.entry = h['location']
    e = Entry(entry_context)
    idelement = e.etree().find("{%s}id" % atompubbase.model.ATOM)
    if None != idelement:
      entry_id = idelement.text
  if None == entry_id:
    info("Atom entry did not contain the required atom:id, can't continue with test.")
    raise StopTest
  return (entry_id, e)

def remove_entries_by_id(entries, ids):
  num_entries = len(ids)
  for econtext in entries:
    e = Entry(econtext)
    idelement = e.etree().find("{%s}id" % atompubbase.model.ATOM)
    if None != idelement and idelement.text in ids:
      info("Remove entry")
      h, b = e.delete()
      check_remove_response(h, b)
      num_entries -= 1
    if num_entries == 0:
      break
  if num_entries == 0:
    success("Removed all entries that we're previously added.")
  
class EntryCollectionTests(Test):
    def __init__(self, collection):
        Test.__init__(self)
        self.collection = collection 

    def testBasic_Entry_Manipulation(self):
        """Add and remove three entries to the collection"""
        info("Service Document: %s" % self.collection.context().collection)

        body = get_test_data("i18n.atom").encode("utf-8")

        h, b = self.collection.get()

        # Add in a slug and category if allowed.
        slugs = []
        ids = []
        added_entries = {}
        for i in range(3):
          info("Create new entry #%d" % (i+1))
          slugs.append("".join([random.choice("abcdefghijkl") for x in range(10)]))
          h, b = self.collection.create(headers = {
            'content-type': 'application/atom+xml',
            'slug': slugs[i]
            },
            body = body % (i+1, repr(time.time())))
          check_create_response(h, b)
          (entry_id, entry) = get_entry_id(self.collection.context(), h, b)
          ids.append(entry_id)
          added_entries[entry_id] = entry
          if i < 2:
            time.sleep(1.1)


        entries = list(self.collection.iter_entry())

        # Entries should appear in reverse chronological order of their creation.
        ids.reverse()
        
        # Confirm the order
        check_order_of_entries(entries, ids)
        
        # Retrieve the second entry added
        entry = added_entries[ids[1]]
        e = entry.etree()
        if e == None:
          raise StopTest

        # Check the slug and links
        check_entry_slug(e, slugs[1])
        check_entry_links(e, ismedia=False)
        
        
        e.find(atompubbase.model.ATOM_TITLE).text = "Internationalization - 2"
        info("Update entry #2 and write back to the collection")
        h, b = entry.put()
        check_update_response(h, b, "Entry #2")

        # Confirm new order
        ids[0:0] = ids[1:2]
        del ids[2]        
        check_order_of_entries(self.collection.iter_entry(), ids)

        # Remove Entries by atom:id
        remove_entries_by_id(self.collection.iter(), ids)
        




class MediaCollectionTests(Test):
    def __init__(self, collection):
        Test.__init__(self)
        self.collection = collection 

    def testBasic_Media_Manipulation(self):
        """Add and remove an image in the collection"""
        info("Service Document: %s" % self.collection.context().collection)
        
        body = get_test_data_raw("success.gif")
        
        info("Create new media entry")
        slug = "".join([random.choice("abcdefghijkl") for x in range(10)])
        h, b = self.collection.create(headers = {
          'content-type': 'image/gif',
          'slug': slug
          },
          body = body)
        check_create_response(h, b)
        entry_id, entry = get_entry_id(self.collection.context(), h, b)

        entries = list(self.collection.iter_entry())

        check_order_of_entries(entries, [entry_id])

        h, b = entry.get()

        e = entry.etree()
        if e == None:
          raise StopTest

        # Check the slug
        check_entry_slug(e, slug)
        check_entry_links(e, ismedia=True)
        
        title = e.find(atompubbase.model.ATOM_TITLE)
        if None == title:
          title = SubElement(e, atompubbase.model.ATOM_TITLE)
        title.text = "Success"
        info("Update Media Link Entry and write back to the collection")
        h, b = entry.put()
        check_update_response(h, b, "Media Link Entry")
        
        # Remove Entry
        info("Remove entry")
        h, b = entry.delete()
        check_remove_response(h, b)
        success("Removed Media Entry")



class TestIntrospection(Test):
    def __init__(self, uri, http):
        Test.__init__(self)
        self.http = http
        self.introspection_uri  = uri

    def testEntry_Collection(self):
        """Find the first entry collection listed in an Introspection document and run the Entry collection tests against it."""
        context = Context(self.http, self.introspection_uri)
        service = Service(context)
        entry_collections = list(service.iter_match("application/atom+xml;type=entry"))
          
        if 0 == len(entry_collections):
          info("Didn't find any Entry Collections to test")
        else:
          test = EntryCollectionTests(Collection(entry_collections[0]))
          test.run()

        media_collections = list(service.iter_match("image/gif"))
          
        if 0 == len(media_collections):
            info("Didn't find any Media Collections that would accept GIF images")
        else:
          test = MediaCollectionTests(Collection(media_collections[0]))
          test.run()

def main(options, cmd_line_args):
    if options.debug:
        httplib2.debuglevel = 5
    if options.verbose:
        recorder.verbosity = 3
    if options.html:
        recorder.html = True

    http = httplib2.Http(MemoryCache())
    http.force_exception_to_status_code = False

    if options.credentials:
      atompubbase.auth.apply_credentials_file(options.credentials, http, error)

    if options.record:
      from atompubbase.mockhttp import MockRecorder
      http = MockRecorder(http, options.record)
    elif options.playback:
      from atompubbase.mockhttp import MockHttp
      http = MockHttp(options.playback)
      

    if not cmd_line_args:
      cmd_line_args = [INTROSPECTION_URI]
    for target_uri in cmd_line_args:
      if not options.quiet:
        print >>sys.stderr, "Testing the service at <%s>" % target_uri
        print >>sys.stderr, "Running: ",
      test = TestIntrospection(target_uri, http)
      test.run()
    if not options.quiet:
      print >>sys.stderr, "\n\n",      
    
    outfile = sys.stdout
    if options.output:
      outfile = file(options.output, "w")

    print >>outfile, recorder.tostr()
    status = 0
    if recorder.has_warnings:
      status = 1
    if recorder.has_errors:
      status = 2

    return status

if __name__ == '__main__':
    sys.exit(main(options, cmd_line_args))
