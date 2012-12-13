SERVICE1 = """<?xml version="1.0" encoding='utf-8'?>
<service xmlns="http://www.w3.org/2007/app">
  <workspace title="Main Site" > 
    <collection 
      title="My Blog Entries" 
      href="http://example.org/reilly/main" />
    <collection 
      title="Pictures" 
      href="http://example.org/reilly/pic" >
      <accept>image/*</accept>
    </collection>
  </workspace>
  <workspace title="Side Bar Blog">
    <collection title="Remaindered Links" 
      href="http://example.org/reilly/list" />
  </workspace>
</service>"""


ENTRY1 = """<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom">
  <title type="text">third</title>
  <id>http://bitworking.org/foo/app/main/third</id>
  <author>
     <name>Joe Gregorio</name>
  </author>
  <updated>2006-08-04T15:52:00-05:00</updated>
  <summary type="html">&lt;p>not much&lt;/p></summary>
  <content type="xhtml">
    <div xmlns="http://www.w3.org/1999/xhtml"><p>Some stuff</p>

      <p><i>[Update: The Atom draft is finished.]</i></p>
      outside a child element.

      <p>More stuff.</p></div>
  </content>
</entry>
"""

import apptools
import unittest
try:
    from xml.etree.ElementTree import fromstring, tostring
except:
    from elementtree.ElementTree import fromstring, tostring
class parseAtomTest(unittest.TestCase):

    def testSimple(self):
        res = apptools.parse_atom_entry(".", fromstring(ENTRY1))
        self.assertEqual(res['title'], "third")
        self.assertEqual(res['summary'], "<p>not much</p>")
        self.assertTrue(res['content'].startswith("""\n    <html:p xmlns:html="http://www.w3.org/1999/xhtml">Some stuff</html:p>"""))

class unparseAtomEntryTest(unittest.TestCase):

    def testEntry(self):
        element = fromstring(ENTRY1)
        d = apptools.parse_atom_entry(".", fromstring(ENTRY1))
        d['content'] = "This is text"
        d['content__type'] = 'text'
        d['summary'] = "<p>This is text</p>"
        d['summary__type'] = 'xhtml'
        apptools.unparse_atom_entry(element, d)
        new_text = tostring(element)
        d = apptools.parse_atom_entry(".", fromstring(new_text))
        self.assertEqual("This is text", d['content'])
        self.assertEqual('<html:p xmlns:html="http://www.w3.org/1999/xhtml">This is text</html:p>', d['summary'])

class wrapTest(unittest.TestCase):

    def testWrap(self):
        self.assertEqual("This\nis", apptools.wrap("This\nis", 80))
        self.assertEqual("This is ", apptools.wrap("This is", 80))
        self.assertEqual("This\nis ", apptools.wrap("This is", 3))
        self.assertEqual("This\nis\n", apptools.wrap("This is\n", 3))

unittest.main()

