import unittest
from model import Context, Service, Collection, Entry
from mockhttp import MockHttp

HTTP_SRC_DIR = "./tests/"

class Test(unittest.TestCase):
    def test_get(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), entry = "http://example.org/entry/67")
        entry = Entry(context)
        (headers, body) = entry.get()
        self.assertEqual(200, headers.status)
        self.assertFalse(entry.has_media())
        self.assertEqual(entry.uri(), "http://example.org/entry/67")

    def test_put(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), entry = "http://example.org/entry/67")
        entry = Entry(context)
        (headers, body) = entry.put(body="<entry></entry>")
        self.assertEqual(200, headers.status)
        self.assertFalse(entry.has_media())
        self.assertEqual(0, len(body))

    def test_delete(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), entry = "http://example.org/entry/67")
        entry = Entry(context)
        (headers, body) = entry.delete()
        self.assertEqual(200, headers.status)
        self.assertFalse(entry.has_media())
        self.assertEqual(0, len(body))

    def test_get_media(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), entry = "http://example.org/images/77")
        entry = Entry(context)
        (headers, body) = entry.get()
        self.assertEqual(200, headers.status)
        self.assertTrue(entry.has_media())
        (headers, body) = entry.get_media()
        self.assertEqual(200, headers.status)
        self.assertTrue(headers['content-type'], 'image/jpg')
        self.assertEqual(7483, len(body))

    def test_put_media(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), entry = "http://example.org/images/77")
        entry = Entry(context)
        (headers, body) = entry.get()
        self.assertEqual(200, headers.status)
        self.assertTrue(entry.has_media())
        (headers, body) = entry.put_media(headers={}, body="")
        self.assertEqual(202, headers.status) # We don't really expect 202 from a PUT, just testing.



if __name__ == "__main__":
    unittest.main()

