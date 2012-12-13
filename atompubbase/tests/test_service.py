import unittest
import model
from model import Context, Service 
from mockhttp import MockHttp
try:
    from xml.etree.ElementTree import fromstring, tostring
except:
    from elementtree.ElementTree import fromstring, tostring

HTTP_SRC_DIR = "./tests/"

class Test(unittest.TestCase):
    def test_get(self):
        c = Context()
        c.service = "http://example.org/service.atomsvc"
        c.http = MockHttp(HTTP_SRC_DIR)
        s = Service(c)
        headers, body = s.get()
        self.assertEqual(headers["status"], "200")
        self.assertEqual(s.uri(), "http://example.org/service.atomsvc")

    def test_iter(self):
        s = Service(Context(http = MockHttp(HTTP_SRC_DIR), service = "http://example.org/service.atomsvc"))
        self.assertEqual("http://example.org/entry/index.atom", s.iter().next().collection)

    def test_iter_match(self):
        s = Service(Context(http = MockHttp(HTTP_SRC_DIR), service = "http://example.org/service_entry_image.atomsvc"))
        self.assertEqual("http://example.org/images/index.atom", s.iter_match('image/png').next().collection)

    def test_iter_match_fail(self):
        s = Service(Context(http = MockHttp(HTTP_SRC_DIR), service = "http://example.org/service.atomsvc"))
        try:
            s.iter_match('image/png').next()
            self.fail("StopIteration should have been raised.")
        except StopIteration:
            pass

    def test_iter_info(self):
        s = Service(Context(http = MockHttp(HTTP_SRC_DIR), service = "http://example.org/service.atomsvc"))
        ws_title, coll_title, coll_uri = s.iter_info().next()
        self.assertEqual("http://example.org/entry/index.atom", coll_uri)
        self.assertEqual("entry", coll_title)
        self.assertEqual("Main Site", ws_title)


    def test_get_child_title(self):
        e = fromstring("<a><title xmlns='http://www.w3.org/2005/Atom'>fred</title></a>")
        self.assertEqual("fred", model.get_child_title(e))
        e = fromstring("<a><title type='html' xmlns='http://www.w3.org/2005/Atom'>fred</title></a>")
        self.assertEqual("fred", model.get_child_title(e))
        e = fromstring("<a><title type='xhtml' xmlns='http://www.w3.org/2005/Atom'><div xmlns='http://www.w3.org/1999/xhtml'>fred <b>and</b> barney.</div></title></a>")
        self.assertEqual("fred and barney.", model.get_child_title(e))



if __name__ == "__main__":
    unittest.main()

