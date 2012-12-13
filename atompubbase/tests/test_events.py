from events import add_event_handlers, register_callback, clear
import unittest

class Entry(object):
    def get(self, headers, body = None):
        return ({}, "foo") 
    
    def put_media(self, headers, body = None):
        return ({'status': '200'}, "bar") 


class Service(object):
    def get(self, headers, body = None):
        return ({'status': '200'}, "baz") 


add_event_handlers(Entry)
add_event_handlers(Service)

class Test(unittest.TestCase):
    def setUp(self):
        self.any_called = False
        self.pre_called = False 
        self.pre_headers = {} 
        self.pre_body = "" 
        self.pre_attribs = set() 
        self.post_called = False 
        self.post_headers = {} 
        self.post_body = "" 
        self.post_attribs = set()
        self.count = 0
        clear()

    def any(self, headers, body, attribs):
        self.any_called = True

    def pre_cb(self, headers, body, attribs):
        self.pre_called = True
        self.pre_headers = headers
        self.pre_body = body
        self.pre_attribs = attribs

    def post_cb(self, headers, body, attribs):
        self.post_called = True
        self.post_headers = headers
        self.post_body = body
        self.post_attribs = attribs

    def inc_cb(self, headers, body, attribs):
        self.count += 1

    def test_any(self):
        """Make sure the right callback is called on ANY"""
        self.assertFalse(self.any_called)
        Entry().get({}, "")
        self.assertFalse(self.any_called)
        register_callback("ANY", self.any)
        Entry().get({}, "")
        self.assertTrue(self.any_called)

    def test_pre(self):
        """Confirm that data is passed through to the callback"""
        register_callback("PRE", self.pre_cb)
        Entry().get({"status": "200"}, "<feed/>")
        self.assertTrue(self.pre_called)
        self.assertEqual(self.pre_headers["status"], "200")
        self.assertEqual(self.pre_body, "<feed/>")
        self.assertTrue("PRE" in self.pre_attribs)
        self.assertTrue("ANY" not in self.pre_attribs)

    def test_post(self):
        """Confirm that data is passed through to the callback"""
        register_callback("POST", self.post_cb)
        headers, body = Entry().put_media({"content-length": "7"}, "<feed/>")
        self.assertTrue(self.post_called)
        self.assertEqual(self.post_headers["status"], "200")
        self.assertEqual(headers["status"], "200")
        self.assertEqual(self.post_body, "bar")
        self.assertEqual(body, "bar")
        self.assertTrue("POST" in self.post_attribs)
        self.assertTrue("ANY" not in self.post_attribs)

    def test_multi_axis_1(self):
        """Test along multiple axes at the same time."""
        register_callback("GET", self.inc_cb)
        register_callback("PRE", self.inc_cb)
        Entry().get({}, "")
        self.assertEqual(self.count, 2)

    def test_multi_axis_2(self):
        """Test along multiple axes at the same time."""
        register_callback("POST_GET", self.inc_cb)
        Entry().get({}, "")
        self.assertEqual(self.count, 1)

    def test_multi_axis_3(self):
        """Test along multiple axes at the same time."""
        register_callback("POST_GET", self.inc_cb)
        register_callback("PRE_ENTRY", self.inc_cb)
        Entry().get({}, "")
        self.assertEqual(self.count, 2)

    def test_multi_axis_4(self):
        """Test along multiple axes at the same time."""
        register_callback("PRE_ANY", self.inc_cb)
        register_callback("POST_GET", self.inc_cb)
        register_callback("PRE_ENTRY", self.inc_cb)
        Entry().get({}, "")
        self.assertEqual(self.count, 3)

    def test_multi_axis_5(self):
        """Test that PRE is not added to ANY"""
        register_callback("ANY", self.inc_cb)
        Entry().get({}, "")
        Entry().put_media({}, "")
        Service().get({}, "")
        self.assertEqual(self.count, 6)

    def test_multi_axis_6(self):
        """Test that manually added PRE/POST works for ANY"""
        register_callback("POST_ANY", self.inc_cb)
        Entry().get({}, "")
        Entry().put_media({}, "")
        Service().get({}, "")
        self.assertEqual(self.count, 3)

    def test_multi_axis_7(self):
        """Test along the class axis."""
        register_callback("PRE_ENTRY", self.inc_cb)
        Entry().get({}, "")
        Entry().put_media({}, "")
        Service().get({}, "")
        self.assertEqual(self.count, 2)

if __name__ == "__main__":
    unittest.main()


