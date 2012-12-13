from model import init_event_handlers, Context, Service, Collection, Entry, ATOM, XHTML
from httplib2 import Http
import unittest
import events

try:
    from xml.etree.ElementTree import fromstring, tostring
except:
    from elementtree.ElementTree import fromstring, tostring

ATOM_CONTENT = "{%s}content/{%s}div" % (ATOM, XHTML)

class Test(unittest.TestCase):
    def test(self):
        c = Context(http = Http(".cache"), service = "http://bitworking.org/projects/apptestsite/app.cgi/service/;service_document")
        s = Service(c)
        collection = Collection(s.iter_match("application/atom+xml;type=entry").next())

        init_event_handlers()
        class EventListener(object):
            events = []
            def callback(self, headers, body, attributes):
                self.events.append(attributes)

        listener = EventListener()
        events.register_callback("ANY", listener.callback)

        CONTENT = """<entry xmlns="http://www.w3.org/2005/Atom">
          <title>Test Post From AtomPubBase Live Test</title>
          <id>urn:uuid:1225c695-ffb8-4ebb-aaaa-80da354efa6a</id>
          <updated>2005-09-02T10:30:00Z</updated>
          <summary>Hi!</summary>
          <author>
            <name>Joe Gregorio</name>
          </author>
          <content>Plain text content for this test.</content>
        </entry>
        """

        entry_context = collection.entry_create(body=CONTENT, headers={'content-type':'application/atom+xml;type=entry'})
        self.assertNotEqual(None, entry_context)
        entry = Entry(entry_context)
        entry.etree().find(ATOM_CONTENT).text = "Bye"
        headers, body = entry.put()
        self.assertEqual(200, headers.status)
        headers, body = entry.delete()
        self.assertEqual(200, headers.status)

        print listener.events 


unittest.main()
