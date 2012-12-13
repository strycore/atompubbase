from pretty import pretty

try:
    from xml.etree.ElementTree import fromstring, tostring
except:
    from elementtree.ElementTree import fromstring, tostring



src = """<html:div xmlns:html="http://www.w3.org/1999/xhtml">
<html:p >I took a couple of days off work 
and we drove down to Florida to visit family in "The Villages", 
a 55+ golf cart community that currently has about 50,000 residents.
</html:p>
<html:p xmlns:html="http://www.w3.org/1999/xhtml">That is not a typo. Check out the <html:a href="http://en.wikipedia.org/wiki/The_Villages">wikipedia</html:a> <html:a href="http://en.wikipedia.org/wiki/The_Villages%2C_Florida">entries</html:a>.
</html:p>
<html:p xmlns:html="http://www.w3.org/1999/xhtml">On Monday we went out to feed the ducks at a nearby pond, but well fed
 by everyone else, they weren't interested in our bread. Instead the bread was 
 attacked from below by the fish in the pond, which wasn't very interesting, that is, until
 a local heron came over and started feasting on the fish we'd attracted. There's nothing
 like the sight of a still living fish wiggling down the throat of a heron to make
 a young boy's day.
</html:p>
<html:table style="width: 194px;" xmlns:html="http://www.w3.org/1999/xhtml"><html:tr><html:td align="center" style="height: 194px;"><html:a href="http://picasaweb.google.com/joe.gregorio/TheVillagesFlorida"><html:img height="160" src="http://lh6.google.com/joe.gregorio/RoK-XGNIkuE/AAAAAAAAAA8/ePqbYyHlxvU/s160-c/TheVillagesFlorida.jpg" style="margin: 1px 0 0 4px;" width="160" /></html:a></html:td></html:tr><html:tr><html:td style="text-align: center; font-family: arial,sans-serif; font-size: 11px;"><html:a href="http://picasaweb.google.com/joe.gregorio/TheVillagesFlorida" style="color: #4D4D4D; font-weight: bold; text-decoration: none;">The Villages, Florida</html:a></html:td></html:tr>
</html:table>
</html:div>"""


print pretty(fromstring(src))
