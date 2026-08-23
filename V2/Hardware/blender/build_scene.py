#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Build the Alphabets V2 rigid-body scene inside Blender."""

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
CODE_DIR = BLENDER_DIR.parents[1] / "Code"
GENERATED_DIR = BLENDER_DIR / "generated"
PAWL_CAPTURE_PATH = GENERATED_DIR / "pawl-position.json"
FLOOR_CAPTURE_PATH = GENERATED_DIR / "floor-position.json"
MM = 0.001
if str(BLENDER_DIR) not in sys.path:
    sys.path.insert(0, str(BLENDER_DIR))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from json_license_metadata import validate_json_license

from license_metadata import apply_blend_license_metadata


def parse_args() -> argparse.Namespace:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=GENERATED_DIR / "alphabets-v2-gravity.blend",
    )
    parser.add_argument(
        "--preview",
        type=Path,
        default=GENERATED_DIR / "alphabets-v2-gravity.png",
    )
    parser.add_argument("--no-simulate", action="store_true")
    parser.add_argument("--long-run", action="store_true")
    return parser.parse_args(arguments)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_json_license(data, str(path))
    return data


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    target.objects.link(obj)


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0,
    roughness: float = 0.45,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    metallic_input = shader.inputs.get("Metallic IOR Level") or shader.inputs.get(
        "Metallic"
    )
    if metallic_input is not None:
        metallic_input.default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if color[3] < 1:
        shader.inputs["Alpha"].default_value = color[3]
        result.surface_render_method = "DITHERED"
    return result


def atlas_material(atlas_path: Path) -> bpy.types.Material:
    result = bpy.data.materials.new("StickerAtlas_BlackWhite")
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    shader = nodes.get("Principled BSDF")
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.name = "International64_Atlas"
    image_node.label = "64 characters / 128 mapped halves"
    image_node.image = bpy.data.images.load(str(atlas_path), check_existing=True)
    image_node.image.pack()
    image_node.interpolation = "Linear"
    uv_node = nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = "AtlasUV"
    links.new(uv_node.outputs["UV"], image_node.inputs["Vector"])
    links.new(image_node.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 0.62
    return result


def card_outline(card: dict[str, float]) -> list[tuple[float, float]]:
    half_width = card["body_width"] / 2
    hinge = card["tab_axis_height"]
    tab_start = card["tab_start_height"]
    total = card["total_height"]
    tab_width = card["tab_width"]
    return [
        (-half_width, -hinge),
        (half_width, -hinge),
        (half_width, tab_start - hinge),
        (half_width + tab_width, tab_start - hinge),
        (half_width + tab_width, total - hinge),
        (-half_width - tab_width, total - hinge),
        (-half_width - tab_width, tab_start - hinge),
        (-half_width, tab_start - hinge),
    ]


def prism_mesh(
    name: str,
    outline_mm: list[tuple[float, float]],
    thickness_mm: float,
) -> bpy.types.Mesh:
    half_thickness = thickness_mm * MM / 2
    vertices = [(x * MM, -half_thickness, z * MM) for x, z in outline_mm] + [
        (x * MM, half_thickness, z * MM) for x, z in outline_mm
    ]
    count = len(outline_mm)
    faces: list[tuple[int, ...]] = [
        tuple(reversed(range(count))),
        tuple(range(count, 2 * count)),
    ]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index, count + index))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return mesh


def polygon_centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Return the area centroid of a simple card outline in millimetres."""

    twice_area = 0.0
    x_sum = 0.0
    z_sum = 0.0
    for index, (x0, z0) in enumerate(points):
        x1, z1 = points[(index + 1) % len(points)]
        cross = x0 * z1 - x1 * z0
        twice_area += cross
        x_sum += (x0 + x1) * cross
        z_sum += (z0 + z1) * cross
    return x_sum / (3 * twice_area), z_sum / (3 * twice_area)


def sticker_mesh(
    name: str,
    card: dict[str, float],
    face: str,
    uv_box: list[float],
    rotation_degrees: int,
    horizontal_flip: bool,
    center_mm: tuple[float, float],
) -> bpy.types.Mesh:
    half_width = card["sticker_width"] * MM / 2
    z0 = (card["sticker_y_offset"] - card["tab_axis_height"]) * MM
    z1 = z0 + card["sticker_face_height"] * MM
    y = card["finished_thickness"] * MM / 2
    if face == "back":
        y = -y
    center_x, center_z = (value * MM for value in center_mm)
    vertices = [
        (-half_width - center_x, y, z0 - center_z),
        (half_width - center_x, y, z0 - center_z),
        (half_width - center_x, y, z1 - center_z),
        (-half_width - center_x, y, z1 - center_z),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    u0, v0, u1, v1 = uv_box
    if rotation_degrees == 0:
        coordinates = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    elif rotation_degrees == 180:
        coordinates = ((u1, v1), (u0, v1), (u0, v0), (u1, v0))
    else:
        raise ValueError(f"unsupported sticker rotation: {rotation_degrees}")
    if horizontal_flip:
        coordinates = tuple((u0 + u1 - u, v) for u, v in coordinates)
    uv_layer = mesh.uv_layers.new(name="AtlasUV")
    for loop, uv in zip(mesh.loops, coordinates, strict=True):
        uv_layer.data[loop.index].uv = uv
    return mesh


def add_rigid_body(
    obj: bpy.types.Object,
    body_type: str,
    collision_shape: str,
) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add()
    obj.select_set(False)
    obj.rigid_body.type = body_type
    obj.rigid_body.collision_shape = collision_shape


def import_structure(
    scene_data: dict[str, Any],
    structure_collection: bpy.types.Collection,
) -> list[bpy.types.Object]:
    imported: list[bpy.types.Object] = []
    for component in scene_data["static_components"]:
        path = GENERATED_DIR / component["file"]
        before = set(bpy.context.scene.objects)
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=MM)
        created = list(set(bpy.context.scene.objects) - before)
        if len(created) != 1:
            raise RuntimeError(f"expected one mesh in {path}, got {len(created)}")
        obj = created[0]
        obj.name = component["name"]
        move_to_collection(obj, structure_collection)
        rgba = tuple(component["color"])
        mat = material(f"Material_{component['name']}", rgba)
        obj.data.materials.append(mat)
        obj["cad_source"] = component["file"]
        imported.append(obj)
    return imported


def cube_object(
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    target_collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_to_collection(obj, target_collection)
    return obj


def build_adjustable_pawl(
    scene_data: dict[str, Any],
    target_collection: bpy.types.Collection,
    pawl_material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a stationary flat pawl with its origin on the lower support edge."""

    pawl = scene_data["pawl"]
    half_width = pawl["width_mm"] * MM / 2
    height = pawl["height_mm"] * MM
    thickness = pawl["thickness_mm"] * MM
    vertices = [
        (-half_width, 0, 0),
        (half_width, 0, 0),
        (-half_width, thickness, 0),
        (half_width, thickness, 0),
        (-half_width, 0, height),
        (half_width, 0, height),
        (-half_width, thickness, height),
        (half_width, thickness, height),
    ]
    faces = [
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    ]
    mesh = bpy.data.meshes.new("CardStopPawlMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    result = bpy.data.objects.new(pawl["name"], mesh)
    target_collection.objects.link(result)
    captured_transform = None
    if PAWL_CAPTURE_PATH.exists():
        candidate = load_json(PAWL_CAPTURE_PATH)
        if (
            candidate.get("object") == pawl["name"]
            and candidate.get("geometry_version") == pawl["geometry_version"]
        ):
            captured_transform = candidate

    if captured_transform is None:
        result.location = tuple(value * MM for value in pawl["support_edge_initial_mm"])
        result["position_source"] = "scene manifest initial position"
    else:
        result.location = tuple(
            value * MM for value in captured_transform["support_edge_world_mm"]
        )
        result.rotation_euler = tuple(
            math.radians(value) for value in captured_transform["rotation_xyz_degrees"]
        )
        result.scale = tuple(captured_transform["scale_xyz"])
        result["position_source"] = str(PAWL_CAPTURE_PATH.name)
    result.data.materials.append(pawl_material)
    add_rigid_body(result, "PASSIVE", "CONVEX_HULL")
    result.rigid_body.friction = 0.5
    result["support_edge_is_object_origin"] = True
    result["geometry_version"] = pawl["geometry_version"]
    result["mount"] = pawl["mount"]
    result["reference_card_01_hole_mm"] = pawl["reference_card_01_hole_mm"]
    result["reference_card_02_hole_mm"] = pawl["reference_card_02_hole_mm"]
    result["flush_reference"] = pawl["flush_reference"]
    result["capture_script"] = "capture_pawl.py"
    return result


def build_floor(
    scene_data: dict[str, Any],
    helpers_collection: bpy.types.Collection,
    floor_material: bpy.types.Material,
    pawl: bpy.types.Object,
    *,
    long_run: bool,
) -> bpy.types.Object:
    floor_data = scene_data["manual_floor"]
    thickness = floor_data["thickness_mm"] * MM
    size = floor_data["size_mm"] * MM
    top_z = floor_data["initial_top_z_mm"] * MM
    floor = cube_object(
        "CompressionFloor_Adjustable",
        (size, size, thickness),
        (0, 0, top_z - thickness / 2),
        helpers_collection,
    )
    captured_transform = None
    if FLOOR_CAPTURE_PATH.exists():
        candidate = load_json(FLOOR_CAPTURE_PATH)
        if (
            candidate.get("object") == floor.name
            and candidate.get("geometry_version") == floor_data["geometry_version"]
        ):
            captured_transform = candidate
    if captured_transform is not None:
        floor.location = tuple(
            value * MM for value in captured_transform["origin_world_mm"]
        )
        floor.rotation_euler = tuple(
            math.radians(value) for value in captured_transform["rotation_xyz_degrees"]
        )
        floor.scale = tuple(captured_transform["scale_xyz"])
        floor["position_source"] = str(FLOOR_CAPTURE_PATH.name)
    else:
        floor["position_source"] = "scene manifest initial position"
    floor.data.materials.append(floor_material)
    add_rigid_body(floor, "PASSIVE", "BOX")
    floor.rigid_body.kinematic = not long_run
    if long_run:
        floor.rigid_body.use_margin = True
        floor.rigid_body.collision_margin = 0.0005
    floor.rigid_body.friction = 0.48
    floor["purpose"] = (
        "Manually positioned compacting plane for discovering the enclosure volume"
    )
    floor["manual_transform"] = True
    floor["geometry_version"] = floor_data["geometry_version"]
    floor["interactive_mode"] = "move on Z while timeline playback is running"
    floor["initial_top_z_mm"] = floor_data["initial_top_z_mm"]
    if long_run:
        top_z = floor_data["long_run_top_z_mm"] * MM
        final_y = pawl.location.y - size / 2
        floor.location = (floor.location.x, final_y, top_z - thickness / 2)
        floor["long_run"] = True
        floor["final_front_edge_y_mm"] = round((final_y + size / 2) / MM, 6)
        floor["final_top_z_mm"] = floor_data["long_run_top_z_mm"]
    return floor


def build_cards(
    scene_data: dict[str, Any],
    mapping_data: dict[str, Any],
    cards_collection: bpy.types.Collection,
    stickers_collection: bpy.types.Collection,
    constraints_collection: bpy.types.Collection,
    helpers_collection: bpy.types.Collection,
    card_material: bpy.types.Material,
    sticker_material: bpy.types.Material,
    long_run: bool,
) -> None:
    card_dimensions = scene_data["card"]
    outline = card_outline(card_dimensions)
    center_mm = polygon_centroid(outline)
    centered_outline = [(x - center_mm[0], z - center_mm[1]) for x, z in outline]
    source_mesh = prism_mesh(
        "CardBlankMesh", centered_outline, card_dimensions["thickness"]
    )
    mapping = {
        assignment["target"]: assignment for assignment in mapping_data["assignments"]
    }
    simulation = scene_data["simulation"]
    center_of_mass_bias_y = simulation["card_center_of_mass_bias_y_mm"] * MM
    release_frames = {
        card_number: simulation["release_start_frame"]
        + order_index * simulation["release_interval_frames"]
        for order_index, card_number in enumerate(simulation["release_order"])
    }

    anchor = cube_object(
        "DrumHingeAnchor",
        (0.002, 0.002, 0.002),
        (0, 0, 0),
        helpers_collection,
    )
    anchor.hide_render = True
    anchor.hide_set(True)
    add_rigid_body(anchor, "ACTIVE", "BOX")
    anchor.rigid_body.kinematic = True
    anchor.rigid_body.mass = 10

    for pose in scene_data["card_poses"]:
        number = pose["card"]
        is_southern = number == 0 or number >= 33
        name = f"card_{number:02d}"
        card = bpy.data.objects.new(name, source_mesh.copy())
        cards_collection.objects.link(card)
        card.data.materials.append(card_material)
        tilt_degrees = 5 if long_run and is_southern else pose["tilt_degrees"]
        tilt = math.radians(tilt_degrees)
        pivot = tuple(value * MM for value in pose["pivot_mm"])
        center_x = center_mm[0] * MM
        center_z = center_mm[1] * MM
        card.location = (
            pivot[0] + center_x,
            pivot[1] - center_z * math.sin(tilt) + center_of_mass_bias_y,
            pivot[2] + center_z * math.cos(tilt),
        )
        card.rotation_euler.x = tilt
        card["card_number"] = number
        card["source_hole_position"] = pose["source_hole_position"]
        card["pivot_mm"] = pose["pivot_mm"]
        card["center_of_mass_bias_y_mm"] = simulation["card_center_of_mass_bias_y_mm"]
        add_rigid_body(card, "ACTIVE", "CONVEX_HULL")
        card.rigid_body.mass = 0.00105
        card.rigid_body.friction = 0.42
        card.rigid_body.restitution = 0.02
        card.rigid_body.linear_damping = 0.12
        card.rigid_body.angular_damping = 0.22
        card.rigid_body.use_margin = True
        card.rigid_body.collision_margin = 0.0001
        card.rigid_body.use_deactivation = False
        release_frame = release_frames[number]
        card.rigid_body.kinematic = True
        card.rigid_body.keyframe_insert(
            data_path="kinematic", frame=max(1, release_frame - 1)
        )
        card.rigid_body.kinematic = False
        card.rigid_body.keyframe_insert(data_path="kinematic", frame=release_frame)
        card["release_frame"] = release_frame

        for face in ("front", "back"):
            sticker_name = f"sticker_{number:02d}_{face}"
            assignment = mapping[sticker_name]
            mesh = sticker_mesh(
                f"{sticker_name}_mesh",
                card_dimensions,
                face,
                assignment["uv_box"],
                assignment["rotation_degrees"],
                assignment["horizontal_flip"],
                center_mm,
            )
            sticker = bpy.data.objects.new(sticker_name, mesh)
            stickers_collection.objects.link(sticker)
            sticker.data.materials.append(sticker_material)
            sticker.parent = card
            sticker.location = (0, 0, 0)
            sticker.rotation_euler = (0, 0, 0)
            sticker["character"] = assignment["character"]
            sticker["character_index"] = assignment["character_index"]
            sticker["display_half"] = assignment["display_half"]
            sticker["rotation_degrees"] = assignment["rotation_degrees"]
            sticker["horizontal_flip"] = assignment["horizontal_flip"]

        bpy.ops.object.empty_add(
            type="PLAIN_AXES",
            radius=0.004,
            location=pivot,
        )
        hinge = bpy.context.object
        hinge.name = f"hinge_{number:02d}"
        hinge.rotation_euler.y = math.radians(90)
        move_to_collection(hinge, constraints_collection)
        bpy.context.view_layer.objects.active = hinge
        bpy.ops.rigidbody.constraint_add()
        hinge.rigid_body_constraint.type = "HINGE"
        hinge.rigid_body_constraint.object1 = card
        hinge.rigid_body_constraint.object2 = anchor
        hinge.rigid_body_constraint.disable_collisions = True
        hinge["axis"] = "world X"


def parent_keep_transform(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    world_transform = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_transform


def build_step_controller(
    scene_data: dict[str, Any],
    target_collection: bpy.types.Collection,
    constraints_collection: bpy.types.Collection,
) -> bpy.types.Object:
    """Create a persistent integer control for one 64-position drum step."""

    step_data = scene_data["drum_step"]
    bpy.ops.object.empty_add(type="CIRCLE", radius=0.018, location=(0, 0, 0))
    controller = bpy.context.object
    controller.name = step_data["controller"]
    move_to_collection(controller, target_collection)
    controller.hide_render = True
    controller[step_data["property"]] = 0
    controller.id_properties_ui(step_data["property"]).update(
        min=0,
        soft_max=1_000_000,
        step=1,
        description="Total completed positions across any number of revolutions",
    )
    controller["degrees_per_step"] = step_data["degrees_per_step"]
    controller["direction"] = step_data["direction"]
    controller["step_duration_frames"] = 96
    controller["settle_frames"] = 96
    controller["steps_per_move"] = 1
    controller["step_busy"] = False
    controller["usage"] = (
        "Use Advance steps in the Alphabets sidebar after READY_TO_ROTATE"
    )
    controller.id_properties_ui("step_duration_frames").update(
        min=6,
        max=120,
        step=1,
        description="Motor movement duration; 96 frames equals four seconds at 24 fps",
    )
    controller.id_properties_ui("steps_per_move").update(
        min=1,
        max=256,
        step=1,
        description="Complete character positions to advance in this operation",
    )

    for name in step_data["rotating_components"]:
        parent_keep_transform(bpy.data.objects[name], controller)

    anchor = bpy.data.objects["DrumHingeAnchor"]
    parent_keep_transform(anchor, controller)
    anchor.rigid_body.kinematic = True
    for hinge in constraints_collection.objects:
        parent_keep_transform(hinge, controller)

    return controller


def point_camera(
    camera: bpy.types.Object,
    target: tuple[float, float, float],
) -> None:
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera_and_lighting() -> None:
    bpy.ops.object.camera_add(location=(0.065, -0.235, 0.045))
    camera = bpy.context.object
    camera.name = "Camera_EnclosureReview"
    camera.data.lens = 62
    point_camera(camera, (0, 0, -0.012))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(0.02, -0.12, 0.16))
    key = bpy.context.object
    key.name = "Key_Area"
    key.data.energy = 24
    key.data.shape = "DISK"
    key.data.size = 0.12
    point_camera(key, (0, 0, 0))

    bpy.ops.object.light_add(type="AREA", location=(-0.14, 0.04, 0.06))
    fill = bpy.context.object
    fill.name = "Fill_Area"
    fill.data.energy = 12
    fill.data.size = 0.10
    point_camera(fill, (0, 0, -0.02))


def configure_scene(scene_data: dict[str, Any]) -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.gravity = (0, 0, -scene_data["simulation"]["gravity_m_s2"])
    scene.frame_start = 1
    scene.frame_end = scene_data["simulation"]["end_frame"]
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.028, 0.032, 0.04)
    scene["simulation_note"] = (
        "Cards release sequentially in physical shingling order. The floor never "
        "moves automatically and must be positioned manually before simulation."
    )
    scene["fabrication_source"] = (
        "CadQuery remains authoritative; Blender is simulation only"
    )


def configure_interactive_viewports() -> None:
    """Save all 3D viewports in Material Preview so the packed atlas is visible."""

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            shading = area.spaces.active.shading
            shading.type = "MATERIAL"
            shading.use_scene_world = False


def main() -> int:
    args = parse_args()
    scene_data = load_json(GENERATED_DIR / "scene.json")
    mapping_data = load_json(GENERATED_DIR / "sticker-mapping.json")
    clear_scene()
    configure_scene(scene_data)

    structure_collection = collection("01_STRUCTURE_CAD")
    cards_collection = collection("02_CARDS_RIGID")
    stickers_collection = collection("03_STICKERS_ATLAS")
    constraints_collection = collection("04_HINGES")
    helpers_collection = collection("05_SIMULATION_HELPERS")
    adjustable_collection = collection("06_ADJUSTABLE_PAWL")
    controller_collection = collection("07_DRUM_STEP_CONTROLLER")

    card_mat = material("Card_Black_0_5mm", (0.006, 0.007, 0.009, 1), roughness=0.7)
    floor_mat = material("Floor_Collider", (0.12, 0.15, 0.2, 0.28), roughness=0.8)
    pawl_mat = material("Pawl_Adjustable_Orange", (1.0, 0.16, 0.015, 1), roughness=0.38)
    sticker_mat = atlas_material(GENERATED_DIR / mapping_data["atlas"]["file"])

    import_structure(scene_data, structure_collection)
    pawl = build_adjustable_pawl(scene_data, adjustable_collection, pawl_mat)
    build_floor(
        scene_data,
        helpers_collection,
        floor_mat,
        pawl,
        long_run=args.long_run,
    )
    build_cards(
        scene_data,
        mapping_data,
        cards_collection,
        stickers_collection,
        constraints_collection,
        helpers_collection,
        card_mat,
        sticker_mat,
        long_run=args.long_run,
    )
    step_controller = build_step_controller(
        scene_data, controller_collection, constraints_collection
    )
    setup_camera_and_lighting()
    configure_interactive_viewports()

    if args.long_run:
        ready_frame = scene_data["manual_floor"]["long_run_ready_frame"]
        scene = bpy.context.scene
        scene.frame_end = scene_data["manual_floor"]["long_run_end_frame"]
        scene.playback_loop_mode = "STOP_END_FRAME"
        scene.timeline_markers.new("READY_TO_ROTATE", frame=ready_frame)
        scene["long_run_note"] = (
            f"Play once to frame {ready_frame}, then use the Alphabets panel to "
            "advance any number of drum steps without a timeline loop."
        )

    scene = bpy.context.scene
    scene.frame_set(1)
    if scene.rigidbody_world:
        scene.rigidbody_world.substeps_per_frame = 32
        scene.rigidbody_world.solver_iterations = 50
        scene.rigidbody_world.point_cache.frame_start = scene.frame_start
        scene.rigidbody_world.point_cache.frame_end = scene.frame_end

    if not args.no_simulate:
        bpy.ops.ptcache.bake_all(bake=True)
        scene.frame_set(scene.frame_end)
    else:
        scene.frame_set(1)

    args.preview.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.preview.resolve())
    bpy.ops.render.render(write_still=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    selected_object = step_controller
    selected_object.select_set(True)
    bpy.context.view_layer.objects.active = selected_object
    apply_blend_license_metadata(scene)
    bpy.ops.file.pack_all()
    # Keep custom SPDX properties inspectable without Blender so the repository
    # auditor can verify that the standalone document carries its licence.
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
