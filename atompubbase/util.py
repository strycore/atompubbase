try:
    from xml.etree.ElementTree import fromstring, tostring, SubElement
    import xml.etree.ElementTree as ElementTree
except:
    from elementtree.ElementTree import fromstring, tostring, SubElement
    import elementtree.ElementTree as ElementTree

class namespace(object):
    def __init__(self, uri):
        self.ns_uri = uri
        self.memoized = {}

    def __call__(self, element):
        if element not in self.memoized:
            self.memoized[element] = "{%s}%s" % (self.ns_uri, element)
        return self.memoized[element]


ATOM = namespace("http://www.w3.org/2005/Atom")
APP = namespace("http://www.w3.org/2007/app")
XHTML = namespace("http://www.w3.org/1999/xhtml")

my_namespaces = {
    "http://www.w3.org/1999/xhtml": "xhtml",
    "http://www.w3.org/2007/app" : "app",
    "http://www.w3.org/2005/Atom" : "atom"
    }

ElementTree._namespace_map.update(my_namespaces)

import re
from urlparse import urljoin
from xml.sax.saxutils import quoteattr, escape
import time
import calendar


def get_element(etree, name):
    value = ""
    if '}' not in name:
        name = ATOM(name)
    l = etree.findall(name)
    if l:
        value = l[0].text
    return value

RFC3339 = re.compile("^(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)T(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)(\.\d*)?" +
                           "(?P<timezone>Z|((?P<tzhour>[+-]\d\d):\d\d))$")    

def get_date(etree, name):
    """
    Returns the Date Construct value as seconds from the epoch
    in UTC. The 'name' should be the element name of an
    RFC 4287 Date Contruct, such as ATOM('published'), ATOM('updated')
    or APP('edited'). The parameter 'etree' in an elementtree
    element. Note that you don't need to add the namespace
    to elements in the ATOM namespace.
    """
    date = get_element(etree, name)
    m = RFC3339.search(date)
    if not m:
        raise ValueError("Not a valid RFC 3339 format.")
    d = m.groupdict()
    ndate = [int(x) for x in [d['year'], d['month'], d['day'], d['hour'], d['minute'], d['second']]]
    ndate.append(0) # weekday
    ndate.append(1) # year day
    if d['timezone'] != 'Z':
        ndate[3] -= int(d['tzhour'])
    ndate.append(0)
    return calendar.timegm(tuple(ndate))
        

def serialize_nons(element, top):
    tag = element.tag.split("}", 1)[1]
    tail = u""
    if element.tail != None:
        tail = escape(element.tail)
    text = u""
    if element.text != None:
        text = element.text
    attribs = " ".join(["%s=%s" % (k, quoteattr(v)) for k, v in element.attrib.iteritems()])
    if attribs:
        attribs = " " + attribs
    if top:
        value = escape(text)
        close = u""
    else:
        value = "<%s%s>%s" % (tag, attribs, escape(text))
        close = "</%s>" % tag
    if value == None:
        value = u""
        
    return value + "".join([serialize_nons(c, False) for c in element.getchildren()]) + close + tail
        

def get_text(name, entry):
    value = ""
    texttype = "text"
    l = entry.findall(ATOM(name))
    if l:
        value = l[0].text
        texttype = mime2atom(l[0].get('type', 'text'))
        if texttype in ["text", "html"]:
            pass
        elif texttype == "xhtml":
            div = l[0].find("{http://www.w3.org/1999/xhtml}div")
            value = serialize_nons(div, True)
        else:
            value = ""
    if value == None:
        value = ""
    return (texttype, value)


def set_text(entry, name, ttype, value):
    elements = entry.findall(ATOM(name))
    if not elements:
        element = SubElement(entry, ATOM(name))
    else:
        element = elements[0]
    element.set('type', ttype)
    [element.remove(e) for e in element.getchildren()]
    if ttype in ["html", "text"]:
        element.text = value
    elif ttype == "xhtml":
        element.text = ""
        try:
            div = fromstring((u"<div xmlns='http://www.w3.org/1999/xhtml'>%s</div>" % value).encode('utf-8'))
            element.append(div)
        except:
            element.text = value
            element.set('type', 'html')


mime_to_atom = {
        "application/xhtml+xml": "xhtml",
        "text/html": "html",
        "text/plain": "text"
        }

def mime2atom(t):
    if t in mime_to_atom:
        return mime_to_atom[t]
    else:
        return t

def wrap(text, width):
    l = 0
    ret = []
    for s in text.split(' '):
        ret.append(s)
        l += len(s)
        nl = s.find('\n') >= 0
        if l > width or nl:
            l = 0
            if not nl:
                ret.append('\n')
        else:
            ret.append(' ')
    return "".join(ret)


