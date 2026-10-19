# Reaper Containment

Browser demo of the [ARC-8 Reaper](../../models/arc8-reaper/) roaming a sealed test chamber.

- **Foot IK**: every leg is a two-bone IK chain solved each frame toward a foot target on the real floor height. Feet step in two alternating groups of four (tetrapod gait); the body tilts to fit the ground under the planted feet.
- **AI**: routes planned with A* on a 0.25 m grid; states for roaming, scanning, alert, threat display, hunting, striking and stalking.
- **Controls**: click the floor to drop a noise lure, or switch to *Stalk cursor*. Toggle the IK and pathing overlay to see the solver.

Open `index.html` in a browser (it loads three.js 0.160.0 from jsDelivr).

To rebuild after changing the model:

```bash
python3 ../../models/arc8-reaper/source/export_web.py ../../models/arc8-reaper/SpiderBot.blend spider.json
python3 build.py
```
