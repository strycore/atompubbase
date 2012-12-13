import unittest
from model import Context, Service, Collection
from mockhttp import MockHttp

HTTP_SRC_DIR = "./tests/"

class Test(unittest.TestCase):
    def test_iter(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/entry/index.atom")
        collection = Collection(context)
        entry_contexts = list(collection.iter())
        self.assertEqual(4, len(entry_contexts))
        self.assertEqual(collection.uri(), "http://example.org/entry/index.atom")
    
        # Now test rewinding, starting the iteration over again.
        context = collection.iter().next()
        self.assertEqual(context.entry, "http://example.org/entry/67")
        self.assertEqual(context.collection, "http://example.org/entry/index.atom")

    def test_iter_empty(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/empty/index.atom")
        collection = Collection(context)
        entry_contexts = list(collection.iter())
        self.assertEqual(0, len(entry_contexts))

    def test_create(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/entry/index.atom")
        collection = Collection(context)
        (headers, body) = collection.create({}, "<entry></entry>") # Obviously illegal Atom entry, but not for the mock
        self.assertEqual(headers.status, 201)
        self.assertEqual(headers['location'], "http://example.org/entry/68")

    def test_create_fail(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/empty/index.atom")
        collection = Collection(context)
        (headers, body) = collection.create({}, "<entry></entry>") # Obviously illegal Atom entry, but not for the mock
        self.assertEqual(headers.status, 404)

    def test_create_convenience(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/entry/index.atom")
        collection = Collection(context)
        entry_context = collection.entry_create({}, "<entry></entry>") # Obviously illegal Atom entry, but not for the mock
        self.assertEqual(entry_context.entry, "http://example.org/entry/68")

    def test_create_convenience_fail(self):
        context = Context(http = MockHttp(HTTP_SRC_DIR), collection = "http://example.org/empty/index.atom")
        collection = Collection(context)
        entry_context = collection.entry_create({}, "<entry></entry>") # Obviously illegal Atom entry, but not for the mock
        self.assertEqual(entry_context, None)



if __name__ == "__main__":
    unittest.main()

