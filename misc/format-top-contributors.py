#!/usr/bin/env python3

import sys

contribs = []
for i, line in enumerate(sys.stdin.readlines()):
    try:
        name, count = line.split("|")
    except ValueError:
        break

    name = name.strip()
    count = "{:,}".format(int(count.strip()))
    contribs.append((name, count))

if len(contribs) != 24:
    print("expecting 24 rows!")
    sys.exit(-1)

print('<table class="table table-condensed table-bordered table-striped">')
print('<tbody>')
print('<tr><th colspan="6">Top </th></tr>')

for i in range(12):
    print('<tr>')
    print('<th>%d</th><td><a href="http://musicbrainz.org/user/%s">%s</a></td><td>%s</td>' % (i+1, contribs[i][0], contribs[i][0], contribs[i][1]))
    print('<th>%d</th><td><a href="http://musicbrainz.org/user/%s">%s</a></td><td>%s</td>' % (i+13, contribs[i+12][0], contribs[i+12][0], contribs[i+12][1]))
    print('</tr>')

print('</tbody>')
print('</table>')
