# ARC-8 "Reaper" Crawler — low-poly mech spider for Unity

Original hostile mech spider in a Synty-style flat-shaded look: crouched hunter stance, spiked knees, blade legs, serrated fangs, glowing core. One skinned mesh, one palette-atlas material, 40-bone generic rig, 7 animation clips.

## Contents
| File | What it is |
|---|---|
| `SpiderBot.fbx` | Mesh + rig + all animations (Unity-ready) |
| `SpiderBot.blend` | Blender source (Blender 4.2+ / 5.x), all actions kept |
| `Textures/` | 512px palette atlases: Albedo + Emission for **Obsidian** (red glow), **Rust** (orange glow), **Void** (purple glow), plus a shared MetallicSmoothness map |
| `Unity/` | Import postprocessor, one-click prefab builder, runtime controller |

## Specs
- ~4.4k triangles, 2.6k verts, 1 material, flat shading
- Size: ~1.5 m leg span, knees ~0.55 m high (scale the prefab freely)
- Rigid skinning (every part follows one bone) — no stretching, clean for LODs
- Bones: `Root > Body > Head > Mandible_L/R, Palp_L/R`, `Body > Abdomen`, `Body > Leg_[L|R][1-4]_Coxa > Femur > Tibia > Foot` (1 = front)

## Animations (30 fps, in place)
| Clip | Frames | Loop | Notes |
|---|---|---|---|
| Idle | 120 | yes | twitchy head snaps, chittering fangs, front legs raised and probing |
| Walk | 24 | yes | alternating tetrapod gait, no slide at **0.65 m/s** |
| Run | 14 | yes | no slide at **1.39 m/s** |
| Threat | 44 | no | rears up, legs spread, fangs flared, shudders |
| Attack | 34 | no | fast coil, double-leg stab + bite at frame ~14 |
| Hit | 16 | no | recoil |
| Death | 50 | no | spasm, collapse, legs splay; holds last pose |

## Unity setup (Built-in, URP or HDRP)
1. Drag the whole folder (FBX, `Textures/`, `Unity/`) into `Assets/`. Keep `Textures` next to the FBX.
2. The postprocessor sets the rig to **Generic**, renames clips (`SpiderBot|Walk` → `Walk`) and makes Idle/Walk/Run loop.
   If you imported the FBX before the scripts, right-click it → **Reimport**.
3. Menu **Tools › SpiderBot › Build Prefabs** — creates materials for your render pipeline, `SpiderBot.controller`
   (Speed blend tree Idle→Walk→Run, Threat/Attack/Hit triggers, Dead bool) and three prefabs in `Prefabs/`.
4. Drop a prefab in the scene, tick **Demo Input** on `SpiderBotController`, press Play:
   WASD move/turn, Shift run, T threat, Space attack, H hit, K die (eyes flicker and fade out).

From your own AI code: `SetSpeed(mps)`, `Threaten()`, `Attack()`, `Hit()`, `Die()`.

## Tips
- Want a different colour? Edit an Albedo PNG — each 128px square is one colour (glows also live in the Emission PNG).
- Add Bloom (post-processing / Volume) — the red eyes, leg lines and the core glowing between the abdomen plates are what sell the menace.
- For procedural foot placement, add Unity's Animation Rigging `TwoBoneIK` on `Femur → Tibia` of each leg; the Walk clip still works as the base layer.
- If it faces backwards in your setup, rotate the child model 180° on Y.
