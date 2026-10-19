"""Assemble index.html: inject the GLB (base64) and palette PNGs (data URIs) into template.html."""
import base64, json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
glb = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'lizard.glb')
tex = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, '..', '..', 'models', 'sand-lizard', 'Textures')
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(here, 'index.html')
pal = {}
for name in ('Desert', 'Dune', 'Ember'):
    data = open(os.path.join(tex, f'T_SandLizard_{name}_Albedo.png'), 'rb').read()
    pal[name] = 'data:image/png;base64,' + base64.b64encode(data).decode()
t = open(os.path.join(here, 'template.html')).read()
t = t.replace('/*GLB_B64*/', base64.b64encode(open(glb, 'rb').read()).decode())
t = t.replace('/*PALETTES*/', json.dumps(pal))
open(out, 'w').write(t)
print('wrote', out, len(t))
