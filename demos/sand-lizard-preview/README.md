# Sand Lizard Field Preview

Browser preview of the [Sand Lizard](../../models/sand-lizard/) in a small desert patch with dunes, rocks and a toppled column.

- Same behaviour as the Unity `SandLizardAI`: basking, wandering around a home spot, push-up displays, fleeing, diving into the sand, swimming under the surface and popping up somewhere safer.
- Ground contact on the dunes: the body fits a plane under all four feet and lifts over crests, each leg is re-solved with two-bone IK onto the real sand height (feet tilt to the slope), and tail segments and the snout lift where they would cut into the sand. Measured over 20 s of roaming: mesh vertices under the sand dropped from 0.34% (up to 4.8 cm deep) to 0.02% (max 5 mm, claw tips).
- Sand effects: grit flicked out by the digging legs, sand piling over the body as it dives head-first, a mound that travels under the surface, a heap it bursts out of, and darker dig scars that fade.
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
