<!-- SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org> -->
<!-- SPDX-License-Identifier: MIT -->

# Blender gravity scene

This directory turns the definitive CadQuery geometry into a Blender rigid-body
review scene. CadQuery remains the fabrication source; Blender is used only to
settle the 64 cards under gravity, inspect stacking, and refine the enclosure.

Build and open the scene with:

```sh
cd V2/Hardware/Final/blender
make setup
make open
```

The generated scene contains one active rigid body and one hinge constraint per
card. Every front/back sticker is a separately named child object, but all 128
faces share one texture atlas. `generated/sticker-mapping.json` records the
character, card face, atlas coordinates, and required rotation.
Lower/front artwork is horizontally flipped in UV space so it reads correctly
after the flap turns into the lower display position.

The simulation deliberately models assembly in two phases:

- frames 1-194: southern cards start vertically downward and northern cards
  start 0.5 degrees away from perfectly upright, toward their falling direction.
  This deterministic imperfection gives gravity a non-zero starting torque.
  Cards are released in physical shingling order:
  rear-to-front through the south, then rear-to-front through the north;
- frames 195-800: the stack settles against the fixed pawl and the manually
  positioned floor.

The provisional CadQuery enclosure is deliberately not imported: this scene is
intended to discover the volume that the new enclosure must provide. The only
lower boundary is `CompressionFloor_Adjustable`, an auxiliary collision plane
that has no animation or keyframes. Move it manually on Z before running the
simulation. It is deliberately oversized and is not enclosure geometry. Walls
should be added only after the settled cards and the pawl define their required
envelope.

## Adjustable card-stop pawl

`CardStopPawl_Adjustable` is a stationary vertical plate, 1 mm thick, in its
own collection. It is not parented to the drum. Its inner face is flush with
the finished front face of vertical `card_01`. Its object origin is centered on
the lower inner support edge, whose Z position is halfway between the axes of
the `card_01` and `card_02` holes. Select it and use Blender's `G`/`R` controls
or the Item panel to refine the placement.

The pawl is part of the simulation because it is what keeps `card_01` vertical
after the card rigid bodies are released. It remains stationary while the drum
and cards move.

## Interactive floor and sticker preview

The generated interactive file is unbaked. `CompressionFloor_Adjustable` is a
passive collider with `Animated` enabled and no keyframes. Start timeline
playback, select the floor, and move it on Z: rigid-body collisions update as
new frames are evaluated. Blender does not solve physics while the timeline is
paused; after changing an already evaluated frame, return to frame 1 to clear
and replay the live cache.

After positioning the floor, save the blend file and persist its exact transform
with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  generated/alphabets-v2-interactive.blend --background \
  --python capture_floor.py
```

This writes `generated/floor-position.json`; subsequent generated scenes reuse
that transform automatically.

## Long-running enclosure capture

Run `make long-run` to build the interactive scene used for enclosure capture.
The floor is already stationary with its top 75 mm below the drum axis and its
front edge below the pawl; it is never swept through the cards. Play once to the
`READY_TO_ROTATE` marker at frame 360, then use the `Alphabets` sidebar to turn
the drum. The scene ends at frame 1,000,000 and playback is configured to stop,
not loop. A five-degree initial fall bias in the southern cards avoids the
perfectly vertical Bullet contact while the stack is being initialized.

The sticker atlas is packed into the blend file, and its 3D viewports are saved
in Material Preview. If a viewport is manually switched to Solid mode, press
`Z` and select `Material Preview` to see the artwork again.

Each generated `.blend` stores its MIT licence and The Beach Lab attribution in
the scene's custom properties and embeds the complete licence text in a text
block named `LICENSE`. Those records remain inside the document when the blend
file is shared on its own.

## Advance the drum for multiple revolutions

The installed `Alphabets Drum Step` add-on exposes an `Alphabets` tab in the 3D
View sidebar. Each step rotates the two drum disks, both structural supports,
the motor shaft, and all 64 hinge axes by exactly `-5.625` degrees around world
X: anticlockwise when viewed from the motor at negative X. `Steps per move` may
be used for several positions; the total step counter continues beyond 64.

Each position uses a 96-frame sinusoidal motor movement followed by 96 settling
frames. The button remains disabled until both phases finish. Cards remain
independent rigid bodies, hinged to a motor-driven kinematic drum body. The scene
uses 32 Bullet substeps per frame and 50 solver iterations. `Reset simulation`
returns to the blank position.

A deterministic 0.05 mm center-of-mass tolerance toward the falling side keeps
an upright card from returning to mathematically perfect equilibrium when it
loses the pawl. This is a simulation tolerance, not a change to card geometry.

After moving the pawl, save the blend file and capture the exact transform with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  generated/alphabets-v2-pawl-layout.blend --background \
  --python capture_pawl.py
```

This writes `generated/pawl-position.json`. The captured value is simulation
evidence only until it is reviewed and transferred into CadQuery dimensions.

## Capture the card envelope for the enclosure

After settling or stepping the cards to the position that must fit inside the
enclosure, save `generated/alphabets-v2-interactive.blend` and run:

```sh
make capture-envelope
```

This measures every evaluated card and sticker vertex at the saved frame and
writes `generated/card-envelope.json`, including the source blend hash, frame,
step position, drum radius, and upper/lower extrema. It is retained as an
independent measurement workflow alongside the captured-card enclosure scene.

## Static 5 × 2 HALLO / WELT! wall

Build the presentation scene with:

```sh
make hello-wall
```

The result is the technical scene
`generated/hello-wall/alphabets-hallo-welt-5x2.blend` plus a JSON manifest. No
render is generated. Its ten modules preserve the current CadQuery enclosure
dimensions and docking pitch. The top row reads `HALLO` and the lower row reads
`WELT!`, representing the spoken phrase `HALLO WELT!` without spending an
eleventh module on the space.

Every module contains both enclosure halves, both drum discs and both drum
supports, all 64 captured cards, all 128 sticker faces, the definitive pawl,
the complete motor reference, four M3 screws and six 3 × 1 mm magnets seated in
their CAD pockets. PCBs and cables remain excluded. Sticker backgrounds use a
low-roughness gloss-black material with yellow Blue Highway lettering from the
production atlas, so every displayed glyph shares its scale and baseline. At
captured display position 37, the requested full glyph is mapped continuously
across `sticker_38_back` above and `sticker_37_front` below.

The file also includes a front orthographic render camera and Blender's packed
`studio.exr` HDRI. The build prepares these resources but does not render an
image.
