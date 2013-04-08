import unittest
from model import Context
import pickle
from StringIO import StringIO


class Test(unittest.TestCase):
    def test_attribs(self):
        c = Context()
        c.service = "http://example.org/service.atomsvc"
        c.collection = "http://example.org/collection/1/"
        c.entry = "http://example.org/collection/1/1"
        self.assertEqual(c.service, "http://example.org/service.atomsvc")
        self.assertEqual(c.collection, "http://example.org/collection/1/")
        self.assertEqual(c.entry, "http://example.org/collection/1/1")

        c.collection = "http://example.org/collection/2/"
        self.assertEqual(c.service, "http://example.org/service.atomsvc")
        self.assertEqual(c.collection, "http://example.org/collection/2/")
        self.assertEqual(c.entry, None)

        service_url = "http://example.org/some_other_service.atomsvc"
        c.service = service_url
        self.assertEqual(c.service, service_url)
        self.assertEqual(c.collection, None)
        self.assertEqual(c.entry, None)

    def test_push_pop(self):
        c = Context()
        c.service = "http://example.org/service.atomsvc"
        c.collection = "http://example.org/collection/1/"
        c.entry = "http://example.org/collection/1/1"

        c.collpush("http://fred.org/")

        # Test pickle and un-pickle while were at it.
        file_handle = StringIO()
        pickle.dump(c, file_handle)
        file_handle.seek(0)
        c = pickle.load(file_handle)

        self.assertEqual(c.collection, "http://fred.org/")
        self.assertEqual(c.entry, None)
        c.collpop()
        self.assertEqual(c.collection, "http://example.org/collection/1/")
        self.assertEqual(c.entry, "http://example.org/collection/1/1")

    def test_restore(self):
        class A(object):
            def __init__(self, context):
                self.context = context

        class B(object):
            def __init__(self, context):
                self.context = context

        class C(object):
            def __init__(self, context):
                self.context = context

        ctxt = Context()
        ctxt.service = "http://example.org/service.atomsvc"
        ctxt.collection = "http://example.org/collection/1/"
        ctxt.entry = "http://example.org/collection/1/1"

        a, b, c = ctxt.restore(A, B, C)
        self.assertEqual(type(a), A)
        self.assertEqual(type(b), B)
        self.assertEqual(type(c), C)

        ctxt.service = None
        a, b, c = ctxt.restore(A, B, C)
        self.assertEqual(a, None)
        self.assertEqual(b, None)
        self.assertEqual(c, None)


if __name__ == "__main__":
    unittest.main()
