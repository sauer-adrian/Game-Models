# Sand Lizard Field Preview

Browser preview of the [Sand Lizard](../../models/sand-lizard/) in a small desert patch with dunes, rocks and a toppled column.

- Same behaviour as the Unity `SandLizardAI`: basking, wandering around a home spot, push-up displays, fleeing, diving into the sand, swimming under the surface (a moving sand mound) and popping up somewhere safer.
- Your cursor is a threat; click to stomp. On phones, tap.
- Turning: slow pivots play the stepping turn clips paced to the real turn rate; moving turns curve the spine and tail.
- The clip panel plays any of the 9 animations on the selected lizard, with walk and run kept in phase while blending.
- 1, 3 or 5 lizards; Desert, Dune or Ember colors; turntable and slow motion.

Open `index.html` in a browser (it loads three.js 0.160.0 from jsDelivr).

To rebuild after changing the model:

```bash
python3 ../../models/sand-lizard/source/export_web.py ../../models/sand-lizard/SandLizard.blend lizard.glb
python3 build.py
```
