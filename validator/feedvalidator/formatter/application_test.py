"""$Id: application_test.py 988 2008-03-12 18:22:48Z sa3ruby $"""

__author__ = "Sam Ruby <http://intertwingly.net/> and Mark Pilgrim <http://diveintomark.org/>"
__version__ = "$Revision: 988 $"
__copyright__ = "Copyright (c) 2002 Sam Ruby and Mark Pilgrim"

"""Output class for testing that all output messages are defined properly"""

from base import BaseFormatter
import feedvalidator
import os
LANGUAGE = os.environ.get('LANGUAGE', 'en')
lang = __import__('feedvalidator.i18n.%s' % LANGUAGE, globals(), locals(), LANGUAGE)

class Formatter(BaseFormatter):
  def getMessage(self, event):
    classes = [event.__class__]
    while len(classes):
      if lang.messages.has_key(classes[0]):
        return lang.messages[classes[0]] % event.params
      classes = classes + list(classes[0].__bases__)
      del classes[0]
    return None
    
  def format(self, event):
    """returns the formatted representation of a single event"""
    return self.getMessage(event)
