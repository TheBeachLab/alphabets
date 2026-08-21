# Blender gravity scene

This directory turns the definitive CadQuery geometry into a Blender rigid-body
review scene. CadQuery remains the fabrication source; Blender is used only to
settle the 64 cards under gravity, inspect stacking, and refine the enclosure.

Build and open the scene with:

```sh
cd V2/Hardware/blender
make setup
make open
```

The generated scene contains one active rigid body and one hinge constraint per
card. Every front/back sticker is a separately named child object, but all 128
faces share one texture atlas. `generated/sticker-mapping.json` records the
character, card face, atlas coordinates, and required rotation.

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

The sticker atlas is packed into the blend file, and its 3D viewports are saved
in Material Preview. If a viewport is manually switched to Solid mode, press
`Z` and select `Material Preview` to see the artwork again.

## Advance exactly one character

The installed `Alphabets Drum Step` add-on exposes an `Alphabets` tab in the 3D
View sidebar. `Advance one character` rotates the two drum disks, motor shaft,
and all 64 hinge axes by exactly `-5.625` degrees around world X: anticlockwise
when viewed from the motor at negative X.

One click creates a 24-frame eased motor movement and then evaluates 24 settling
frames. The button remains disabled until both phases finish. Cards remain
independent rigid bodies. The scene uses 32 Bullet substeps per frame and 50
solver iterations so a 0.7 mm finished card cannot tunnel through its neighbor
during a normal step. `Reset simulation` returns to the blank position.

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
