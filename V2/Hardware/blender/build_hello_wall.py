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
from mathutils import Matrix, Vector

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


def remap_display_uv(mesh: bpy.types.Mesh, assignment: dict[str, Any]) -> None:
    uv_layer = mesh.uv_layers.active or mesh.uv_layers.new(name="DisplayUV")
    u0, v0, u1, v1 = assignment["uv_box"]
    rotation = assignment["rotation_degrees"]
    if rotation == 0:
        coordinates = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    elif rotation == 180:
        coordinates = ((u1, v1), (u0, v1), (u0, v0), (u1, v0))
    else:
        raise ValueError(f"unsupported sticker rotation: {rotation}")
    if assignment["horizontal_flip"]:
        coordinates = tuple((u0 + u1 - u, v) for u, v in coordinates)
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
    scene["motor_included"] = True
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
            area.spaces.active.shading.use_scene_world = True
            region = area.spaces.active.region_3d
            region.view_distance = 0.46
            region.view_location = (0, -0.012, -0.003)


def configure_camera_and_hdri(
    target: bpy.types.Collection,
    limits: dict[str, float],
) -> None:
    resources = Path("/Applications/Blender.app/Contents/Resources")
    candidates = sorted(resources.glob("*/datafiles/studiolights/world/studio.exr"))
    if not candidates:
        raise FileNotFoundError("Blender studio.exr HDRI")

    world = bpy.data.worlds.get("Alphabets_Studio_HDRI") or bpy.data.worlds.new(
        "Alphabets_Studio_HDRI"
    )
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.name = "Packed_Blender_Studio_HDRI"
    environment.image = bpy.data.images.load(str(candidates[-1]), check_existing=True)
    environment.image.pack()
    background.inputs["Strength"].default_value = 0.65
    world.node_tree.links.new(environment.outputs["Color"], background.inputs["Color"])
    world.node_tree.links.new(
        background.outputs["Background"], output.inputs["Surface"]
    )
    bpy.context.scene.world = world

    camera_data = bpy.data.cameras.new("Camera_HALLO_WELT_Front")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.37
    camera = bpy.data.objects.new("Camera_HALLO_WELT_Front", camera_data)
    target.objects.link(camera)
    center_y = (limits["back_y"] + limits["front_y"]) * MM / 2
    camera.location = (0, 1.2, -0.003)
    direction = Vector((0, center_y, -0.003)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera["purpose"] = "front render camera; no render generated by build"
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene["hdri"] = "Blender studio.exr (packed)"


def build_screws(
    *,
    prefix: str,
    root: bpy.types.Object,
    target: bpy.types.Collection,
    meshes: dict[str, dict[str, bpy.types.Mesh]],
    fasteners: list[dict[str, Any]],
) -> None:
    for fastener in fasteners:
        label = str(fastener["name"])
        for part, position_key in (
            ("shaft", "shaft_center_mm"),
            ("head", "head_center_mm"),
            ("slot_a", "slot_center_mm"),
            ("slot_b", "slot_center_mm"),
        ):
            obj = clone_mesh_object(
                name=f"ScrewM3_{label}_{part}_{prefix}",
                mesh=meshes[label][part],
                local_matrix=translation_mm(*fastener[position_key]),
                parent=root,
                target=target,
            )
            obj["fastener"] = "M3"
            obj["fastener_role"] = label
            obj["cad_derived_position"] = True


def build_magnets(
    *,
    prefix: str,
    root: bpy.types.Object,
    target: bpy.types.Collection,
    mesh: bpy.types.Mesh,
    placements: list[dict[str, Any]],
) -> None:
    for placement in placements:
        magnet = clone_mesh_object(
            name=f"Magnet_{placement['name']}_{prefix}",
            mesh=mesh,
            local_matrix=translation_mm(*placement["center_mm"]),
            parent=root,
            target=target,
        )
        magnet["diameter_mm"] = 3.0
        magnet["thickness_mm"] = 1.0
        magnet["located_from_cad_pocket"] = True


def main() -> int:
    args = parse_args()
    if not SOURCE_BLEND.exists():
        raise FileNotFoundError(SOURCE_BLEND)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
    capture = load_json(CAPTURE_PATH)
    enclosure_manifest = load_json(MECHANICAL_OUTPUT / "manifest.json")
    hello_manifest = load_json(OUTPUT_DIR / "manifest.json")
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
        name: {
            key: bpy.data.objects[name][key]
            for key in tuple(bpy.data.objects[name].keys())
        }
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
        "motors": collection("07_MOTORS_NO_CABLES"),
        "magnets": collection("08_MAGNETS"),
        "camera": collection("09_CAMERA_AND_HDRI"),
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
        "motor": material(
            "Motor_Steel", (0.42, 0.44, 0.47, 1), metallic=0.72, roughness=0.24
        ),
        "backpack": material(
            "Motor_Backpack_Blue", (0.025, 0.12, 0.5, 1), roughness=0.32
        ),
        "shaft": material(
            "Motor_Shaft_Steel", (0.55, 0.58, 0.62, 1), metallic=0.86, roughness=0.18
        ),
        "magnet": material(
            "Magnet_Nickel", (0.58, 0.61, 0.66, 1), metallic=0.95, roughness=0.14
        ),
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

    motor_meshes = {}
    for component in hello_manifest["motor_components"]:
        name = component["name"]
        mesh = imported_stl_mesh(OUTPUT_DIR / component["file"], name)
        assign_material(
            mesh,
            materials["backpack"]
            if name == "motor_backpack"
            else materials["shaft"]
            if name == "motor_shaft"
            else materials["motor"],
        )
        motor_meshes[name] = mesh

    screw_meshes = {}
    for fastener in hello_manifest["fasteners"]:
        name = fastener["name"]
        axis = fastener["axis"]
        slot_dimensions = (
            ((0.12, 3.8, 0.45), (0.12, 0.45, 3.8))
            if axis == "X"
            else ((3.8, 0.12, 0.45), (0.45, 0.12, 3.8))
        )
        screw_meshes[name] = {
            "shaft": primitive_cylinder_mesh(
                f"M3_{name}_shaft",
                fastener["shaft_diameter_mm"] / 2,
                fastener["shaft_depth_mm"],
                axis,
            ),
            "head": primitive_cylinder_mesh(
                f"M3_{name}_head",
                fastener["head_diameter_mm"] / 2,
                fastener["head_depth_mm"],
                axis,
            ),
            "slot_a": primitive_box_mesh(f"M3_{name}_slot_a", slot_dimensions[0]),
            "slot_b": primitive_box_mesh(f"M3_{name}_slot_b", slot_dimensions[1]),
        }
        for part, mesh in screw_meshes[name].items():
            assign_material(
                mesh,
                materials["slot"] if part.startswith("slot") else materials["steel"],
            )

    magnet_mesh = primitive_cylinder_mesh(
        "Magnet_3x1",
        hello_manifest["magnets"]["diameter_mm"] / 2,
        hello_manifest["magnets"]["thickness_mm"],
        "Z",
    )
    assign_material(magnet_mesh, materials["magnet"])

    capture_matrices = {
        f"card_{int(item['card_number']):02d}": Matrix(item["matrix_world"])
        for item in capture["cards"]
    }
    pitch_x = enclosure_manifest["parameters"]["minimum_same_orientation_pitch"]
    pitch_z = limits["outer_top_z"] - limits["outer_bottom_z"]
    module_manifest = {
        (item["row"], item["column"]): item for item in hello_manifest["modules"]
    }

    for row, text in enumerate(ROWS, start=1):
        center_z = pitch_z / 2 if row == 1 else -pitch_z / 2
        for column_index, character in enumerate(text, start=1):
            module_data = module_manifest[(row, column_index)]
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
            root["motor_included"] = True

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

            for source_name, mesh in motor_meshes.items():
                motor = clone_mesh_object(
                    name=f"Motor_{source_name}_{prefix}",
                    mesh=mesh,
                    local_matrix=Matrix.Identity(4),
                    parent=root,
                    target=collections["motors"],
                )
                motor["cad_component"] = source_name
                motor["electronics"] = False
                motor["cables_included"] = False

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
                        assign_material(sticker_mesh, materials["sticker"])
                        remap_display_uv(
                            sticker_mesh,
                            module_data["production_atlas_uv"][display_half],
                        )
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
                        sticker["typography"] = "production atlas shared scale"

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
                fasteners=hello_manifest["fasteners"],
            )
            build_magnets(
                prefix=prefix,
                root=root,
                target=collections["magnets"],
                mesh=magnet_mesh,
                placements=hello_manifest["magnets"]["placements"],
            )

    forbidden_tokens = ("electronics_card", "pcb", "cable")
    leaked = sorted(
        obj.name
        for obj in bpy.context.scene.objects
        if any(token in obj.name.lower() for token in forbidden_tokens)
    )
    if leaked:
        raise RuntimeError(f"electronics leaked into the scene: {leaked}")

    configure_camera_and_hdri(collections["camera"], limits)
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
