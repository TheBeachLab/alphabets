#!/usr/bin/env python3
"""Build a static 5 x 2 HALLO/WELT! product scene in Blender."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
OUTPUT_DIR = BLENDER_DIR / "generated/hello-wall"
MECHANICAL_OUTPUT = V2_DIR / "Hardware/mechanical/generated/captured-enclosure"
MM = 0.001


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "alphabets-hallo-welt-5x2.blend",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=OUTPUT_DIR / "alphabets-hallo-welt-5x2.png",
    )
    return parser.parse_args(arguments)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)
    for child in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(child)
        bpy.data.collections.remove(child)


def child_collection(name: str, parent: bpy.types.Collection) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    parent.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def principled_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0,
    roughness: float = 0.4,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    metallic_input = shader.inputs.get("Metallic IOR Level") or shader.inputs.get(
        "Metallic"
    )
    if metallic_input is not None:
        metallic_input.default_value = metallic
    return result


def sticker_material(character: str, texture_path: Path) -> bpy.types.Material:
    result = bpy.data.materials.new(f"Sticker_GlossBlack_Yellow_{character}")
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    shader = nodes.get("Principled BSDF")
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.name = f"Texture_{character}"
    image_node.image = bpy.data.images.load(str(texture_path), check_existing=True)
    image_node.image.pack()
    image_node.interpolation = "Linear"
    links.new(image_node.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.08
    coat = shader.inputs.get("Coat Weight") or shader.inputs.get("Clearcoat")
    if coat is not None:
        coat.default_value = 0.45
    emission_color = shader.inputs.get("Emission Color") or shader.inputs.get(
        "Emission"
    )
    emission_strength = shader.inputs.get("Emission Strength")
    if emission_color is not None:
        links.new(image_node.outputs["Color"], emission_color)
    if emission_strength is not None:
        emission_strength.default_value = 0.0
    return result


def import_stl_mesh(path: Path, name: str) -> bpy.types.Mesh:
    before = set(bpy.context.scene.objects)
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=MM)
    created = list(set(bpy.context.scene.objects) - before)
    if len(created) != 1:
        raise RuntimeError(f"expected one object from {path}, got {len(created)}")
    obj = created[0]
    mesh = obj.data
    mesh.name = f"{name}_LinkedMesh"
    bpy.data.objects.remove(obj, do_unlink=True)
    return mesh


def mesh_instance(
    name: str,
    mesh: bpy.types.Mesh,
    target: bpy.types.Collection,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.parent = parent
    return obj


def add_bevel(obj: bpy.types.Object, width_mm: float, segments: int = 3) -> None:
    modifier = obj.modifiers.new("Manufactured edge bevel", "BEVEL")
    modifier.width = width_mm * MM
    modifier.segments = segments


def box_object(
    name: str,
    dimensions_mm: tuple[float, float, float],
    location_mm: tuple[float, float, float],
    target: bpy.types.Collection,
    material: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    bevel_mm: float = 0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(value * MM for value in dimensions_mm)
    obj.location = tuple(value * MM for value in location_mm)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target)
    obj.data.materials.append(material)
    if parent is not None:
        obj.parent = parent
    if bevel_mm:
        add_bevel(obj, bevel_mm)
    return obj


def cylinder_object(
    name: str,
    radius_mm: float,
    depth_mm: float,
    location_mm: tuple[float, float, float],
    axis: str,
    target: bpy.types.Collection,
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    rotation = {
        "X": (0, math.pi / 2, 0),
        "Y": (math.pi / 2, 0, 0),
        "Z": (0, 0, 0),
    }[axis]
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=radius_mm * MM,
        depth=depth_mm * MM,
        location=tuple(value * MM for value in location_mm),
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, target)
    obj.data.materials.append(material)
    obj.parent = parent
    add_bevel(obj, min(0.3, depth_mm / 4), segments=3)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def sticker_mesh(
    name: str, width_mm: float, height_mm: float, uv_v: tuple[float, float]
) -> bpy.types.Mesh:
    half_width = width_mm * MM / 2
    half_height = height_mm * MM / 2
    vertices = [
        (-half_width, 0, -half_height),
        (-half_width, 0, half_height),
        (half_width, 0, half_height),
        (half_width, 0, -half_height),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    v0, v1 = uv_v
    # A camera on the enclosure's +Y/front side sees Blender world X reversed.
    # Flip U once so the artwork remains readable from the physical front.
    coordinates = ((1, v0), (1, v1), (0, v1), (0, v0))
    uv_layer = mesh.uv_layers.new(name="StickerUV")
    for loop, uv in zip(mesh.loops, coordinates, strict=True):
        uv_layer.data[loop.index].uv = uv
    return mesh


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_module(
    *,
    row: int,
    column: int,
    character: str,
    center_x_mm: float,
    center_z_mm: float,
    limits: dict[str, float],
    upper_mesh: bpy.types.Mesh,
    lower_mesh: bpy.types.Mesh,
    pawl_mesh: bpy.types.Mesh,
    materials: dict[str, bpy.types.Material],
    collections: dict[str, bpy.types.Collection],
    texture_path: Path,
) -> bpy.types.Object:
    prefix = f"R{row}C{column}_{character.replace('!', 'EXCL')}"
    bpy.ops.object.empty_add(
        type="PLAIN_AXES",
        location=(center_x_mm * MM, 0, center_z_mm * MM),
    )
    root = bpy.context.object
    root.name = f"Module_{prefix}"
    move_to_collection(root, collections["roots"])
    root["row"] = row
    root["column"] = column
    root["character"] = character
    root["electronics_included"] = False

    upper = mesh_instance(
        f"EnclosureUpper_{prefix}", upper_mesh, collections["enclosures"], root
    )
    lower = mesh_instance(
        f"EnclosureLower_{prefix}", lower_mesh, collections["enclosures"], root
    )
    pawl = mesh_instance(f"Pawl_{prefix}", pawl_mesh, collections["enclosures"], root)
    for obj in (upper, lower, pawl):
        obj["cad_geometry"] = True

    card_y = limits["front_y"] - 0.5
    for half, z in (("upper", 24.0), ("lower", -24.0)):
        card = box_object(
            f"Card_{prefix}_{half}",
            (50.0, 0.7, 48.0),
            (0, card_y, z),
            collections["cards"],
            materials["card"],
            root,
            bevel_mm=0.35,
        )
        card["display_half"] = half

    sticker_mat = sticker_material(character, texture_path)
    sticker_y = limits["front_y"] - 0.08
    sticker_gap = 0.5
    half_height = 45.5
    for half, z, uv_v in (
        ("upper", sticker_gap / 2 + half_height / 2, (0.5, 1.0)),
        ("lower", -sticker_gap / 2 - half_height / 2, (0.0, 0.5)),
    ):
        mesh = sticker_mesh(f"StickerMesh_{prefix}_{half}", 45.0, half_height, uv_v)
        sticker = bpy.data.objects.new(f"Sticker_{prefix}_{half}", mesh)
        collections["stickers"].objects.link(sticker)
        sticker.parent = root
        sticker.location = (0, sticker_y * MM, z * MM)
        sticker.data.materials.append(sticker_mat)
        sticker["character"] = character
        sticker["display_half"] = half
        sticker["finish"] = "gloss black with yellow lettering"

    pawl_axis_z = (limits["inner_top_z"] + limits["outer_top_z"]) / 2
    pawl_outer_y = limits["front_y"] + 2.0
    cylinder_object(
        f"ScrewPawlShaft_M3_{prefix}",
        1.5,
        8.0,
        (0, limits["front_y"] - 4.0, pawl_axis_z),
        "Y",
        collections["screws"],
        materials["steel"],
        root,
    )
    cylinder_object(
        f"ScrewPawlHead_M3_{prefix}",
        3.0,
        1.8,
        (0, pawl_outer_y - 0.9, pawl_axis_z),
        "Y",
        collections["screws"],
        materials["steel"],
        root,
    )
    for slot_name, dimensions in (
        ("horizontal", (3.8, 0.12, 0.45)),
        ("vertical", (0.45, 0.12, 3.8)),
    ):
        box_object(
            f"ScrewPawlSlot_{slot_name}_{prefix}",
            dimensions,
            (0, pawl_outer_y + 0.02, pawl_axis_z),
            collections["screws"],
            materials["slot"],
            root,
        )

    shaft_recess_x = limits["outer_x_max"] - 6.0
    cylinder_object(
        f"ScrewAxleShaft_M3_{prefix}",
        1.5,
        21.0,
        (shaft_recess_x - 12.5, 0, 0),
        "X",
        collections["screws"],
        materials["steel"],
        root,
    )
    cylinder_object(
        f"ScrewAxleHead_M3_{prefix}",
        3.0,
        2.0,
        (shaft_recess_x - 1.0, 0, 0),
        "X",
        collections["screws"],
        materials["steel"],
        root,
    )
    return root


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = "MILLIMETERS"
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.004, 0.005, 0.008, 1)
    background.inputs["Strength"].default_value = 0.03
    scene.view_settings.exposure = -0.7
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene["title"] = "HALLO / WELT! - 5 x 2 Alphabets modules"
    scene["display_rows"] = ["HALLO", "WELT!"]
    scene["spoken_message"] = "HALLO WELT!"
    scene["electronics_included"] = False
    scene["fabrication_source"] = "CadQuery captured enclosure STL"


def setup_studio(
    collections: dict[str, bpy.types.Collection],
    background_material: bpy.types.Material,
) -> None:
    box_object(
        "StudioBackdrop",
        (560, 5, 420),
        (0, -82, 0),
        collections["studio"],
        background_material,
    )

    bpy.ops.object.camera_add(location=(0, 1.15, 0.01))
    camera = bpy.context.object
    camera.name = "Camera_HALLO_WELT_Front"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.39
    point_at(camera, (0, 0, 0))
    move_to_collection(camera, collections["camera"])
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("Key_Softbox", (-0.24, 0.32, 0.26), 42, 0.28),
        ("Fill_Softbox", (0.28, 0.24, 0.08), 24, 0.24),
        ("Top_Rim", (0.0, 0.05, 0.38), 32, 0.20),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, (0, 0, 0))
        move_to_collection(light, collections["lights"])


def configure_viewports() -> None:
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            shading = area.spaces.active.shading
            shading.type = "MATERIAL"
            shading.use_scene_world = True


def main() -> int:
    args = parse_args()
    manifest = load_json(OUTPUT_DIR / "manifest.json")
    enclosure_manifest = load_json(MECHANICAL_OUTPUT / "manifest.json")
    limits = enclosure_manifest["limits_mm"]
    clear_scene()
    configure_scene()

    root_collection = bpy.data.collections.new("ALPHABETS_HALLO_WELT_5x2")
    bpy.context.scene.collection.children.link(root_collection)
    collections = {
        "roots": child_collection("00_MODULE_ROOTS", root_collection),
        "enclosures": child_collection("01_ENCLOSURES_CAD", root_collection),
        "cards": child_collection("02_CARDS", root_collection),
        "stickers": child_collection("03_STICKERS_GLOSS_BLACK_YELLOW", root_collection),
        "screws": child_collection("04_M3_SCREWS", root_collection),
        "studio": child_collection("05_STUDIO", root_collection),
        "lights": child_collection("06_LIGHTS", root_collection),
        "camera": child_collection("07_CAMERA", root_collection),
    }

    materials = {
        "enclosure": principled_material(
            "Enclosure_Graphite", (0.018, 0.022, 0.03, 1), roughness=0.24
        ),
        "card": principled_material(
            "Card_Black_0_7mm", (0.003, 0.004, 0.006, 1), roughness=0.58
        ),
        "steel": principled_material(
            "M3_Screw_Steel", (0.32, 0.36, 0.42, 1), metallic=0.92, roughness=0.18
        ),
        "slot": principled_material(
            "Screw_Slot_Dark", (0.008, 0.009, 0.012, 1), roughness=0.5
        ),
        "background": principled_material(
            "Studio_Black", (0.002, 0.003, 0.006, 1), roughness=0.32
        ),
    }
    upper_mesh = import_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-upper.stl",
        "EnclosureUpper",
    )
    lower_mesh = import_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-lower.stl",
        "EnclosureLower",
    )
    pawl_mesh = import_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-pawl-definitive.stl",
        "PawlDefinitive",
    )
    for mesh in (upper_mesh, lower_mesh, pawl_mesh):
        mesh.materials.append(materials["enclosure"])

    column_pitch = enclosure_manifest["parameters"]["minimum_same_orientation_pitch"]
    row_pitch = limits["outer_top_z"] - limits["outer_bottom_z"]
    rows = manifest["display_rows"]
    roots = []
    for row_index, row in enumerate(rows, start=1):
        center_z = row_pitch / 2 if row_index == 1 else -row_pitch / 2
        for column_index, character in enumerate(row, start=1):
            # Front viewing from +Y reverses Blender world X on screen.
            center_x = (3 - column_index) * column_pitch
            roots.append(
                build_module(
                    row=row_index,
                    column=column_index,
                    character=character,
                    center_x_mm=center_x,
                    center_z_mm=center_z,
                    limits=limits,
                    upper_mesh=upper_mesh,
                    lower_mesh=lower_mesh,
                    pawl_mesh=pawl_mesh,
                    materials=materials,
                    collections=collections,
                    texture_path=OUTPUT_DIR
                    / manifest["modules"][(row_index - 1) * 5 + column_index - 1][
                        "texture"
                    ],
                )
            )

    forbidden = ("motor", "electronic", "pcb", "backpack", "cable")
    forbidden_objects = [
        obj.name
        for obj in bpy.context.scene.objects
        if any(x in obj.name.lower() for x in forbidden)
    ]
    if forbidden_objects:
        raise RuntimeError(f"electronics leaked into scene: {forbidden_objects}")
    if len(roots) != 10:
        raise RuntimeError(f"expected ten modules, got {len(roots)}")

    setup_studio(collections, materials["background"])
    configure_viewports()
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(args.preview.resolve())
    bpy.ops.render.render(write_still=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    roots[0].select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
