from __future__ import annotations

from generate_assets import (
    EXCLUDED_STATIC_COMPONENTS,
    NORTH_FALL_BIAS_DEGREES,
    build_scene_manifest,
    build_sticker_mapping,
)


def test_provisional_enclosure_is_excluded_from_blender_scene() -> None:
    assert EXCLUDED_STATIC_COMPONENTS == {"enclosure_lower", "enclosure_upper"}


def test_mapping_assigns_every_card_face_exactly_once() -> None:
    mapping = build_sticker_mapping()
    assignments = mapping["assignments"]
    targets = [assignment["target"] for assignment in assignments]
    assert len(assignments) == 128
    assert len(set(targets)) == 128
    assert set(targets) == {
        f"sticker_{card:02d}_{face}" for card in range(64) for face in ("front", "back")
    }


def test_mapping_wraps_blank_a_and_degree_in_travel_order() -> None:
    assignments = {
        assignment["target"]: assignment
        for assignment in build_sticker_mapping()["assignments"]
    }
    assert assignments["sticker_00_front"]["character"] == " "
    assert assignments["sticker_01_back"]["character"] == " "
    assert assignments["sticker_01_front"]["character"] == "A"
    assert assignments["sticker_02_back"]["character"] == "A"
    assert assignments["sticker_63_front"]["character"] == "°"
    assert assignments["sticker_00_back"]["character"] == "°"


def test_upper_and_lower_halves_keep_the_cut_edge_at_the_hinge() -> None:
    assignments = build_sticker_mapping()["assignments"]
    front = next(item for item in assignments if item["target"] == "sticker_01_front")
    back = next(item for item in assignments if item["target"] == "sticker_02_back")
    assert front["display_half"] == "lower"
    assert front["center_cut_edge"] == "top"
    assert front["rotation_degrees"] == 0
    assert back["display_half"] == "upper"
    assert back["center_cut_edge"] == "bottom"
    assert back["rotation_degrees"] == 180
    assert front["target_edge"] == back["target_edge"] == "hinge"


def test_scene_numbering_starts_lower_then_upper_then_incoming() -> None:
    scene = build_scene_manifest([])
    poses = {pose["card"]: pose for pose in scene["card_poses"]}
    assert poses[0]["pivot_mm"][2] < 0
    assert poses[1]["pivot_mm"][2] > 0
    assert poses[2]["pivot_mm"][2] > poses[1]["pivot_mm"][2]
    assert all(
        pose["tilt_degrees"] == 0 for pose in poses.values() if pose["pivot_mm"][2] < 0
    )
    assert all(
        pose["tilt_degrees"] == 180 - NORTH_FALL_BIAS_DEGREES
        for pose in poses.values()
        if pose["pivot_mm"][2] > 0
    )
    assert scene["simulation"]["north_fall_bias_degrees"] == 0.5
    assert scene["simulation"]["card_center_of_mass_bias_y_mm"] == 0.05
    assert scene["drum_step"] == {
        "controller": "DrumStepController",
        "property": "step_count",
        "degrees_per_step": -5.625,
        "direction": "anticlockwise from motor side at negative X",
        "rotating_components": ["motor_side", "shaft_side", "motor_shaft"],
    }
    assert "enclosure" not in scene
    assert scene["manual_floor"] == {
        "geometry_version": 1,
        "size_mm": 250,
        "thickness_mm": 2,
        "initial_top_z_mm": -95,
    }
    release_order = scene["simulation"]["release_order"]
    assert len(release_order) == len(set(release_order)) == 64
    assert release_order[:3] == [33, 34, 35]
    assert release_order[30:34] == [63, 0, 32, 31]
    assert release_order[-1] == 1
    pawl = scene["pawl"]
    hole_01 = pawl["reference_card_01_hole_mm"]
    hole_02 = pawl["reference_card_02_hole_mm"]
    assert pawl["thickness_mm"] == 1
    assert pawl["height_mm"] == 8
    assert pawl["support_edge_initial_mm"][0] == 0
    assert pawl["support_edge_initial_mm"][1] == round(
        hole_01[1] + scene["card"]["finished_thickness"] / 2, 9
    )
    assert pawl["support_edge_initial_mm"][2] == round((hole_01[2] + hole_02[2]) / 2, 9)
    assert (
        min(hole_01[2], hole_02[2])
        < pawl["support_edge_initial_mm"][2]
        < max(hole_01[2], hole_02[2])
    )
