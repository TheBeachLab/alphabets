"""Blender add-on for physically simulated Alphabets drum steps."""

from __future__ import annotations

import math

import bpy

bl_info = {
    "name": "Alphabets Drum Step",
    "author": "Alphabets",
    "version": (1, 1, 1),
    "blender": (5, 2, 0),
    "location": "3D View > Sidebar > Alphabets",
    "description": "Advance the 64-position drum by configurable physical steps",
    "category": "Animation",
}

CONTROLLER_NAME = "DrumStepController"
TOTAL_STEPS = 64


def controller_object() -> bpy.types.Object | None:
    return bpy.data.objects.get(CONTROLLER_NAME)


def extend_simulation_range(scene: bpy.types.Scene, end_frame: int) -> None:
    """Keep the scene and Bullet cache ranges aligned for appended steps."""

    scene.frame_end = max(scene.frame_end, end_frame)
    if scene.rigidbody_world is not None:
        point_cache = scene.rigidbody_world.point_cache
        point_cache.frame_end = max(point_cache.frame_end, end_frame)


def ensure_controller_properties(controller: bpy.types.Object) -> None:
    """Add controls introduced after a blend file was originally generated."""

    if "steps_per_move" not in controller:
        controller["steps_per_move"] = 1
    controller.id_properties_ui("steps_per_move").update(
        min=1,
        max=TOTAL_STEPS,
        step=1,
        description="Number of complete character positions to advance",
    )
    controller.id_properties_ui("step_count").update(
        min=0,
        max=TOTAL_STEPS,
        step=1,
        description="Completed character positions since reset",
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

    controller.rotation_mode = "XYZ"
    controller.rotation_euler.x = math.radians(current_step * degrees_per_step)
    controller.keyframe_insert(data_path="rotation_euler", index=0, frame=start_frame)
    controller.rotation_euler.x = math.radians(target_step * degrees_per_step)
    controller.keyframe_insert(data_path="rotation_euler", index=0, frame=motor_end)

    action = controller.animation_data.action if controller.animation_data else None
    if action is not None and hasattr(action, "fcurves"):
        for curve in action.fcurves:
            if curve.data_path != "rotation_euler" or curve.array_index != 0:
                continue
            for point in curve.keyframe_points:
                if start_frame <= point.co.x <= motor_end:
                    point.interpolation = "SINE"
                    point.easing = "EASE_IN_OUT"

    controller["step_count"] = target_step
    controller["step_busy"] = True
    controller["busy_until_frame"] = settle_end
    return target_step, motor_end, settle_end


def insert_smooth_steps(
    controller: bpy.types.Object,
    start_frame: int,
    requested_steps: int,
) -> tuple[int, int, int]:
    """Insert up to ``requested_steps`` complete move-and-settle cycles."""

    current_step = int(controller.get("step_count", 0))
    remaining_steps = max(0, TOTAL_STEPS - current_step)
    step_total = min(max(0, requested_steps), remaining_steps)
    if step_total == 0:
        return current_step, start_frame, start_frame

    motor_end = start_frame
    settle_end = start_frame
    target_step = current_step
    for _ in range(step_total):
        target_step, motor_end, settle_end = insert_smooth_step(controller, settle_end)
    return target_step, motor_end, settle_end


class ALPHABETS_OT_advance_one(bpy.types.Operator):
    bl_idname = "alphabets.advance_one_character"
    bl_label = "Advance character steps"
    bl_description = "Advance the selected number of positions, settling every step"

    _timer = None
    _settle_end = 0

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        controller = controller_object()
        return (
            controller is not None
            and not bool(controller.get("step_busy", False))
            and int(controller.get("step_count", 0)) < TOTAL_STEPS
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
        if self._settle_end == scene.frame_current:
            self.report({"INFO"}, "The drum is already at position 64")
            return {"CANCELLED"}
        scene.playback_loop_mode = "STOP_END_FRAME"
        extend_simulation_range(scene, self._settle_end)
        self.report({"INFO"}, f"Advancing to position {target_step}")
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
        current_step = int(controller["step_count"])
        requested_steps = int(controller["steps_per_move"])
        actual_steps = min(requested_steps, max(0, TOTAL_STEPS - current_step))
        layout.label(text=f"Position: {current_step} / {TOTAL_STEPS}")
        layout.prop(controller, '["steps_per_move"]', text="Steps per move")
        layout.prop(controller, '["step_duration_frames"]', text="Motor frames")
        row = layout.row()
        row.enabled = not bool(controller.get("step_busy", False)) and actual_steps > 0
        label = f"Advance {actual_steps} step" + ("s" if actual_steps != 1 else "")
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
