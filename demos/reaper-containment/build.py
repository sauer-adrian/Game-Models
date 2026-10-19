"""Rebuild index.html: injects spider.json (exported by models/arc8-reaper/source/export_web.py) into template.html."""
import os
here = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(here, 'template.html')).read()
d = open(os.path.join(here, 'spider.json')).read()
open(os.path.join(here, 'index.html'), 'w').write(t.replace('/*SPIDER_DATA*/', d))
