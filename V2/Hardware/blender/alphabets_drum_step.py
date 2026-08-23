# SPDX-FileCopyrightText: 2014-2026 The Beach Lab <https://beachlab.org>
# SPDX-License-Identifier: MIT
"""Blender add-on for long-running physically simulated Alphabets drum steps."""

from __future__ import annotations

import math

import bpy

bl_info = {
    "name": "Alphabets Drum Step",
    "author": "Alphabets",
    "version": (1, 2, 0),
    "blender": (5, 2, 0),
    "location": "3D View > Sidebar > Alphabets",
    "description": "Advance the 64-position drum for multiple revolutions",
    "category": "Animation",
}

CONTROLLER_NAME = "DrumStepController"
TOTAL_POSITIONS = 64
MAX_STEPS = 1_000_000


def controller_object() -> bpy.types.Object | None:
    return bpy.data.objects.get(CONTROLLER_NAME)


def extend_simulation_range(scene: bpy.types.Scene, end_frame: int) -> None:
    """Keep the scene and Bullet cache ranges aligned without shortening either."""

    point_cache = (
        scene.rigidbody_world.point_cache if scene.rigidbody_world is not None else None
    )
    target_end = max(
        scene.frame_end,
        end_frame,
        point_cache.frame_end if point_cache is not None else end_frame,
    )
    scene.frame_end = target_end
    if point_cache is not None:
        point_cache.frame_end = target_end


def ensure_controller_properties(controller: bpy.types.Object) -> None:
    """Add controls introduced after a blend file was generated."""

    if "steps_per_move" not in controller:
        controller["steps_per_move"] = 1
    controller.id_properties_ui("steps_per_move").update(
        min=1,
        max=256,
        step=1,
        description="Complete character positions to advance in this operation",
    )
    controller.id_properties_ui("step_count").update(
        min=0,
        max=MAX_STEPS,
        step=1,
        description="Total completed positions; values above 64 are additional turns",
    )


def insert_smooth_step(
    controller: bpy.types.Object,
    start_frame: int,
) -> tuple[int, int, int]:
    """Insert one eased motor step and return target, motor end, and settle end."""

    current_step = int(controller.get("step_count", 0))
    target_step = current_step + 1
    duration = int(controller.get("step_duration_frames", 24))
    settle_frames = int(controller.get("settle_frames", 24))
    degrees_per_step = float(controller["degrees_per_step"])
    motor_end = start_frame + duration
    settle_end = motor_end + settle_frames

    previous_interpolation = (
        bpy.context.preferences.edit.keyframe_new_interpolation_type
    )
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "SINE"
    try:
        controller.rotation_mode = "XYZ"
        controller.rotation_euler.x = math.radians(current_step * degrees_per_step)
        controller.keyframe_insert(
            data_path="rotation_euler", index=0, frame=start_frame
        )
        controller.rotation_euler.x = math.radians(target_step * degrees_per_step)
        controller.keyframe_insert(data_path="rotation_euler", index=0, frame=motor_end)
    finally:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = (
            previous_interpolation
        )

    controller["step_count"] = target_step
    controller["step_busy"] = True
    controller["busy_until_frame"] = settle_end
    return target_step, motor_end, settle_end


def insert_smooth_steps(
    controller: bpy.types.Object,
    start_frame: int,
    requested_steps: int,
) -> tuple[int, int, int]:
    """Append complete move-and-settle cycles without a one-revolution limit."""

    step_total = max(1, min(int(requested_steps), 256))
    motor_end = start_frame
    settle_end = start_frame
    target_step = int(controller.get("step_count", 0))
    for _ in range(step_total):
        target_step, motor_end, settle_end = insert_smooth_step(controller, settle_end)
    return target_step, motor_end, settle_end


class ALPHABETS_OT_advance_one(bpy.types.Operator):
    bl_idname = "alphabets.advance_one_character"
    bl_label = "Advance character steps"
    bl_description = "Advance the selected positions, settling after every step"

    _timer = None
    _settle_end = 0

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        controller = controller_object()
        return (
            controller is not None
            and not bool(controller.get("step_busy", False))
            and int(controller.get("step_count", 0)) < MAX_STEPS
        )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        controller = controller_object()
        if controller is None:
            self.report({"ERROR"}, f"{CONTROLLER_NAME} is missing")
            return {"CANCELLED"}

        ensure_controller_properties(controller)
        scene = context.scene
        requested_steps = int(controller.get("steps_per_move", 1))
        target_step, _, self._settle_end = insert_smooth_steps(
            controller, scene.frame_current, requested_steps
        )
        scene.playback_loop_mode = "STOP_END_FRAME"
        extend_simulation_range(scene, self._settle_end)
        self.report(
            {"INFO"},
            f"Position {target_step % TOTAL_POSITIONS:02d}; total step {target_step}",
        )
        fps = scene.render.fps / scene.render.fps_base
        self._timer = context.window_manager.event_timer_add(
            1 / fps, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        if event.type == "ESC":
            self.cancel(context)
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        scene = context.scene
        if scene.frame_current < self._settle_end:
            scene.frame_set(scene.frame_current + 1)
            return {"RUNNING_MODAL"}

        self._finish(context)
        return {"FINISHED"}

    def _finish(self, context: bpy.types.Context) -> None:
        controller = controller_object()
        if controller is not None:
            controller["step_busy"] = False
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def cancel(self, context: bpy.types.Context) -> None:
        self._finish(context)


class ALPHABETS_OT_reset_simulation(bpy.types.Operator):
    bl_idname = "alphabets.reset_simulation"
    bl_label = "Reset simulation"
    bl_description = "Return to the blank position and clear live rigid-body state"

    def execute(self, context: bpy.types.Context):
        controller = controller_object()
        if controller is None:
            return {"CANCELLED"}
        controller.animation_data_clear()
        controller.rotation_euler.x = 0
        controller["step_count"] = 0
        controller["step_busy"] = False
        controller["busy_until_frame"] = 1
        context.scene.frame_set(1)
        try:
            bpy.ops.ptcache.free_bake_all()
        except RuntimeError:
            pass
        return {"FINISHED"}


class ALPHABETS_PT_drum_step(bpy.types.Panel):
    bl_label = "Alphabets drum"
    bl_idname = "ALPHABETS_PT_drum_step"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Alphabets"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        controller = controller_object()
        if controller is None:
            layout.label(text="DrumStepController missing", icon="ERROR")
            return
        ensure_controller_properties(controller)
        completed = int(controller["step_count"])
        position = completed % TOTAL_POSITIONS
        revolutions, _ = divmod(completed, TOTAL_POSITIONS)
        layout.label(text=f"Position: {position:02d} / 63")
        layout.label(text=f"Completed turns: {revolutions}")
        layout.prop(controller, '["steps_per_move"]', text="Steps per move")
        layout.prop(controller, '["step_duration_frames"]', text="Motor frames")
        row = layout.row()
        row.enabled = not bool(controller.get("step_busy", False))
        requested = int(controller["steps_per_move"])
        label = f"Advance {requested} step" + ("s" if requested != 1 else "")
        row.operator(ALPHABETS_OT_advance_one.bl_idname, text=label, icon="PLAY")
        layout.operator(ALPHABETS_OT_reset_simulation.bl_idname, icon="LOOP_BACK")


CLASSES = (
    ALPHABETS_OT_advance_one,
    ALPHABETS_OT_reset_simulation,
    ALPHABETS_PT_drum_step,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
