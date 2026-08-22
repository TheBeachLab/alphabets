#!/usr/bin/env python3
"""Build ten complete captured Alphabets mechanisms as a 5 x 2 Blender wall."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Matrix

BLENDER_DIR = Path(__file__).resolve().parent
V2_DIR = BLENDER_DIR.parents[1]
OUTPUT_DIR = BLENDER_DIR / "generated/hello-wall"
SOURCE_BLEND = BLENDER_DIR / "generated/alphabets-v2-card-positions.blend"
CAPTURE_PATH = BLENDER_DIR / "generated/cards-position-capture.json"
MECHANICAL_OUTPUT = V2_DIR / "Hardware/mechanical/generated/captured-enclosure"
MM = 0.001
ROWS = ("HALLO", "WELT!")
DRUM_PARTS = ("motor_side", "shaft_side", "support_front", "support_back")
DISPLAY_LOWER_STICKER = "sticker_37_front"
DISPLAY_UPPER_STICKER = "sticker_38_back"


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "alphabets-hallo-welt-5x2.blend",
    )
    return parser.parse_args(arguments)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0,
    roughness: float = 0.4,
) -> bpy.types.Material:
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
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


def texture_filename(character: str) -> str:
    return "exclamation.png" if character == "!" else f"{character}.png"


def character_material(character: str) -> bpy.types.Material:
    result = bpy.data.materials.new(f"Sticker_GlossBlack_Yellow_{character}")
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    shader = nodes.get("Principled BSDF")
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.image = bpy.data.images.load(
        str(OUTPUT_DIR / "textures" / texture_filename(character)),
        check_existing=True,
    )
    image_node.image.pack()
    links.new(image_node.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.08
    coat = shader.inputs.get("Coat Weight") or shader.inputs.get("Clearcoat")
    if coat is not None:
        coat.default_value = 0.45
    return result


def yellow_atlas_material(image: bpy.types.Image) -> bpy.types.Material:
    result = bpy.data.materials.new("StickerAtlas_GlossBlack_Yellow")
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    shader = nodes.get("Principled BSDF")
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.name = "International64_BlackYellow_Atlas"
    image_node.image = image
    grayscale = nodes.new("ShaderNodeRGBToBW")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.08
    ramp.color_ramp.elements[0].color = (0.001, 0.001, 0.002, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (1.0, 0.62, 0.0, 1)
    links.new(image_node.outputs["Color"], grayscale.inputs["Color"])
    links.new(grayscale.outputs["Val"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.08
    coat = shader.inputs.get("Coat Weight") or shader.inputs.get("Clearcoat")
    if coat is not None:
        coat.default_value = 0.45
    return result


def assign_material(mesh: bpy.types.Mesh, value: bpy.types.Material) -> None:
    mesh.materials.clear()
    mesh.materials.append(value)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def clear_loaded_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for child in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(child)
    for existing in list(bpy.data.collections):
        bpy.data.collections.remove(existing)


def imported_stl_mesh(path: Path, name: str) -> bpy.types.Mesh:
    before = set(bpy.context.scene.objects)
    bpy.ops.wm.stl_import(filepath=str(path), global_scale=MM)
    created = list(set(bpy.context.scene.objects) - before)
    if len(created) != 1:
        raise RuntimeError(f"expected one object from {path}, got {len(created)}")
    obj = created[0]
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    mesh = obj.data
    mesh.name = f"{name}_CAD_Mesh"
    bpy.data.objects.remove(obj, do_unlink=True)
    return mesh


def clone_mesh_object(
    *,
    name: str,
    mesh: bpy.types.Mesh,
    local_matrix: Matrix,
    parent: bpy.types.Object,
    target: bpy.types.Collection,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = local_matrix
    return obj


def remap_display_uv(mesh: bpy.types.Mesh, display_half: str) -> None:
    uv_layer = mesh.uv_layers.active or mesh.uv_layers.new(name="DisplayUV")
    if display_half == "lower":
        coordinates = ((1, 0), (0, 0), (0, 0.5), (1, 0.5))
    elif display_half == "upper":
        coordinates = ((1, 1), (0, 1), (0, 0.5), (1, 0.5))
    else:
        raise ValueError(display_half)
    if len(uv_layer.data) != 4:
        raise RuntimeError(f"unexpected sticker UV loop count: {len(uv_layer.data)}")
    for loop, uv in zip(mesh.loops, coordinates, strict=True):
        uv_layer.data[loop.index].uv = uv


def primitive_cylinder_mesh(
    name: str,
    radius_mm: float,
    depth_mm: float,
    axis: str,
) -> bpy.types.Mesh:
    rotations = {
        "X": (0, math.pi / 2, 0),
        "Y": (math.pi / 2, 0, 0),
        "Z": (0, 0, 0),
    }
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=radius_mm * MM,
        depth=depth_mm * MM,
        rotation=rotations[axis],
    )
    obj = bpy.context.object
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mesh = obj.data
    mesh.name = f"{name}_Mesh"
    bpy.data.objects.remove(obj, do_unlink=True)
    return mesh


def primitive_box_mesh(
    name: str,
    dimensions_mm: tuple[float, float, float],
) -> bpy.types.Mesh:
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(value * MM for value in dimensions_mm)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mesh = obj.data
    mesh.name = f"{name}_Mesh"
    bpy.data.objects.remove(obj, do_unlink=True)
    return mesh


def translation_mm(x: float, y: float, z: float) -> Matrix:
    return Matrix.Translation((x * MM, y * MM, z * MM))


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.name = "ALPHABETS_HALLO_WELT_TECHNICAL"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.frame_start = 1
    scene.frame_end = 1
    scene["title"] = "HALLO / WELT! - ten complete Alphabets mechanisms"
    scene["display_rows"] = list(ROWS)
    scene["spoken_message"] = "HALLO WELT!"
    scene["electronics_included"] = False
    scene["source_capture"] = str(CAPTURE_PATH.relative_to(V2_DIR))
    scene["display_lower_sticker"] = DISPLAY_LOWER_STICKER
    scene["display_upper_sticker"] = DISPLAY_UPPER_STICKER
    scene["render_generated"] = False


def configure_viewports() -> None:
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.spaces.active.shading.type = "MATERIAL"
            area.spaces.active.shading.use_scene_world = False
            region = area.spaces.active.region_3d
            region.view_distance = 0.46
            region.view_location = (0, -0.012, -0.003)


def build_screws(
    *,
    prefix: str,
    root: bpy.types.Object,
    target: bpy.types.Collection,
    meshes: dict[str, bpy.types.Mesh],
    limits: dict[str, float],
) -> None:
    pawl_z = (limits["inner_top_z"] + limits["outer_top_z"]) / 2
    screw_specs = (
        ("PawlShaft", "pawl_shaft", (0, limits["front_y"] - 3.5, pawl_z)),
        ("PawlHead", "pawl_head", (0, limits["front_y"] + 1.5, pawl_z)),
        ("PawlSlotH", "slot_h", (0, limits["front_y"] + 2.01, pawl_z)),
        ("PawlSlotV", "slot_v", (0, limits["front_y"] + 2.01, pawl_z)),
        ("AxleShaft", "axle_shaft", (limits["outer_x_max"] - 10.5, 0, 0)),
        ("AxleHead", "axle_head", (limits["outer_x_max"] - 1.0, 0, 0)),
    )
    for label, mesh_name, position in screw_specs:
        obj = clone_mesh_object(
            name=f"ScrewM3_{label}_{prefix}",
            mesh=meshes[mesh_name],
            local_matrix=translation_mm(*position),
            parent=root,
            target=target,
        )
        obj["fastener"] = "M3"


def main() -> int:
    args = parse_args()
    if not SOURCE_BLEND.exists():
        raise FileNotFoundError(SOURCE_BLEND)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
    capture = load_json(CAPTURE_PATH)
    enclosure_manifest = load_json(MECHANICAL_OUTPUT / "manifest.json")
    limits = enclosure_manifest["limits_mm"]

    card_mesh = bpy.data.objects["card_00"].data
    sticker_templates = {
        f"sticker_{number:02d}_{face}": bpy.data.objects[
            f"sticker_{number:02d}_{face}"
        ].data
        for number in range(64)
        for face in ("front", "back")
    }
    sticker_properties = {
        name: {key: bpy.data.objects[name][key] for key in bpy.data.objects[name]}
        for name in sticker_templates
    }
    source_atlas_material = bpy.data.materials["StickerAtlas_BlackWhite"]
    source_atlas_image = next(
        node.image
        for node in source_atlas_material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image is not None
    )
    drum_templates = {
        name: (bpy.data.objects[name].data, bpy.data.objects[name].matrix_world.copy())
        for name in DRUM_PARTS
    }
    clear_loaded_scene()
    configure_scene()

    root_collection = collection("00_MODULE_ROOTS")
    collections = {
        "enclosure": collection("01_ENCLOSURE_CAD"),
        "drum": collection("02_DRUM_CAD"),
        "cards": collection("03_CARDS_CAPTURED"),
        "stickers": collection("04_STICKERS"),
        "pawl": collection("05_PAWL_DEFINITIVE"),
        "screws": collection("06_M3_SCREWS"),
    }

    materials = {
        "enclosure": material(
            "Enclosure_Opaque_Graphite", (0.025, 0.03, 0.04, 1), roughness=0.3
        ),
        "drum": material("Drum_Dark_Acrylic", (0.09, 0.1, 0.12, 1), roughness=0.4),
        "support": material("Drum_Support", (0.16, 0.17, 0.19, 1), roughness=0.42),
        "card": material("Card_Black_0_5mm", (0.004, 0.005, 0.007, 1), roughness=0.62),
        "sticker": yellow_atlas_material(source_atlas_image),
        "steel": material(
            "M3_Screw_Steel", (0.32, 0.35, 0.4, 1), metallic=0.9, roughness=0.18
        ),
        "slot": material("Screw_Slot_Dark", (0.005, 0.006, 0.008, 1), roughness=0.5),
    }
    assign_material(card_mesh, materials["card"])
    for sticker_mesh in sticker_templates.values():
        assign_material(sticker_mesh, materials["sticker"])
    for name, (mesh, _) in drum_templates.items():
        assign_material(
            mesh, materials["drum"] if "side" in name else materials["support"]
        )

    enclosure_upper = imported_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-upper.stl", "EnclosureUpper"
    )
    enclosure_lower = imported_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-lower.stl", "EnclosureLower"
    )
    pawl_mesh = imported_stl_mesh(
        MECHANICAL_OUTPUT / "print/captured-enclosure-pawl-definitive.stl",
        "PawlDefinitive",
    )
    for mesh in (enclosure_upper, enclosure_lower, pawl_mesh):
        assign_material(mesh, materials["enclosure"])

    screw_meshes = {
        "pawl_shaft": primitive_cylinder_mesh("M3PawlShaft", 1.5, 8.0, "Y"),
        "pawl_head": primitive_cylinder_mesh("M3PawlHead", 3.0, 1.0, "Y"),
        "slot_h": primitive_box_mesh("PawlHeadSlotH", (3.8, 0.12, 0.45)),
        "slot_v": primitive_box_mesh("PawlHeadSlotV", (0.45, 0.12, 3.8)),
        "axle_shaft": primitive_cylinder_mesh("M3AxleShaft", 1.5, 21.0, "X"),
        "axle_head": primitive_cylinder_mesh("M3AxleHead", 3.0, 2.0, "X"),
    }
    for name, mesh in screw_meshes.items():
        assign_material(
            mesh, materials["slot"] if name.startswith("slot") else materials["steel"]
        )

    capture_matrices = {
        f"card_{int(item['card_number']):02d}": Matrix(item["matrix_world"])
        for item in capture["cards"]
    }
    pitch_x = enclosure_manifest["parameters"]["minimum_same_orientation_pitch"]
    pitch_z = limits["outer_top_z"] - limits["outer_bottom_z"]
    character_materials = {
        character: character_material(character)
        for character in dict.fromkeys("".join(ROWS))
    }

    for row, text in enumerate(ROWS, start=1):
        center_z = pitch_z / 2 if row == 1 else -pitch_z / 2
        for column_index, character in enumerate(text, start=1):
            prefix = (
                f"R{row}C{column_index}_{'EXCL' if character == '!' else character}"
            )
            center_x = (3 - column_index) * pitch_x
            root = bpy.data.objects.new(f"Module_{prefix}", None)
            root.empty_display_type = "PLAIN_AXES"
            root.empty_display_size = 0.012
            root.location = (center_x * MM, 0, center_z * MM)
            root_collection.objects.link(root)
            root["row"] = row
            root["column"] = column_index
            root["character"] = character
            root["complete_mechanism"] = True
            root["electronics_included"] = False

            for label, mesh in (("Upper", enclosure_upper), ("Lower", enclosure_lower)):
                obj = clone_mesh_object(
                    name=f"Enclosure{label}_{prefix}",
                    mesh=mesh,
                    local_matrix=Matrix.Identity(4),
                    parent=root,
                    target=collections["enclosure"],
                )
                obj["cad_geometry"] = True

            for source_name, (mesh, world_matrix) in drum_templates.items():
                obj = clone_mesh_object(
                    name=f"Drum_{source_name}_{prefix}",
                    mesh=mesh,
                    local_matrix=world_matrix,
                    parent=root,
                    target=collections["drum"],
                )
                obj["cad_component"] = source_name
                obj["capture_rotation_degrees"] = capture["controller"][
                    "rotation_x_degrees"
                ]

            for number in range(64):
                card_name = f"card_{number:02d}"
                matrix = capture_matrices[card_name]
                card = clone_mesh_object(
                    name=f"Card_{number:02d}_{prefix}",
                    mesh=card_mesh,
                    local_matrix=matrix,
                    parent=root,
                    target=collections["cards"],
                )
                card["card_number"] = number
                card["captured_pose"] = True

                for face in ("front", "back"):
                    source_sticker = f"sticker_{number:02d}_{face}"
                    base_mesh = sticker_templates[source_sticker]
                    display_half = None
                    if source_sticker == DISPLAY_LOWER_STICKER:
                        display_half = "lower"
                    elif source_sticker == DISPLAY_UPPER_STICKER:
                        display_half = "upper"
                    sticker_mesh = base_mesh
                    if display_half is not None:
                        sticker_mesh = base_mesh.copy()
                        sticker_mesh.name = (
                            f"DisplayStickerMesh_{display_half}_{prefix}"
                        )
                        assign_material(sticker_mesh, character_materials[character])
                        remap_display_uv(sticker_mesh, display_half)
                    sticker = clone_mesh_object(
                        name=f"Sticker_{number:02d}_{face}_{prefix}",
                        mesh=sticker_mesh,
                        local_matrix=matrix,
                        parent=root,
                        target=collections["stickers"],
                    )
                    sticker["source_sticker"] = source_sticker
                    sticker["finish"] = "gloss black"
                    for key, value in sticker_properties[source_sticker].items():
                        sticker[f"atlas_{key}"] = value
                    if display_half is not None:
                        sticker["display_character"] = character
                        sticker["display_half"] = display_half
                        sticker["letter_color"] = "yellow"

            pawl = clone_mesh_object(
                name=f"PawlDefinitive_{prefix}",
                mesh=pawl_mesh,
                local_matrix=Matrix.Identity(4),
                parent=root,
                target=collections["pawl"],
            )
            pawl["replaceable"] = True
            pawl["fastener"] = "M3 self-tapping"
            build_screws(
                prefix=prefix,
                root=root,
                target=collections["screws"],
                meshes=screw_meshes,
                limits=limits,
            )

    forbidden_exact = {
        "motor_body",
        "motor_collar",
        "motor_backpack",
        "motor_shaft",
        "electronics_card_envelope",
    }
    leaked = sorted(
        obj.name for obj in bpy.context.scene.objects if obj.name in forbidden_exact
    )
    if leaked:
        raise RuntimeError(f"electronics leaked into the scene: {leaked}")

    configure_viewports()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = bpy.data.objects["Module_R1C1_H"]
    bpy.data.objects["Module_R1C1_H"].select_set(True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
