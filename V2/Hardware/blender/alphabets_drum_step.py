"""Blender add-on for one physically simulated Alphabets drum step."""

from __future__ import annotations

import math

import bpy

bl_info = {
    "name": "Alphabets Drum Step",
    "author": "Alphabets",
    "version": (1, 0, 0),
    "blender": (5, 2, 0),
    "location": "3D View > Sidebar > Alphabets",
    "description": "Advance the 64-position drum by one smooth physical step",
    "category": "Animation",
}

CONTROLLER_NAME = "DrumStepController"


def controller_object() -> bpy.types.Object | None:
    return bpy.data.objects.get(CONTROLLER_NAME)


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


class ALPHABETS_OT_advance_one(bpy.types.Operator):
    bl_idname = "alphabets.advance_one_character"
    bl_label = "Advance one character"
    bl_description = "Rotate the drum exactly 5.625 degrees and settle the cards"

    _timer = None
    _settle_end = 0

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        controller = controller_object()
        return controller is not None and not bool(controller.get("step_busy", False))

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        controller = controller_object()
        if controller is None:
            self.report({"ERROR"}, f"{CONTROLLER_NAME} is missing")
            return {"CANCELLED"}

        scene = context.scene
        _, _, self._settle_end = insert_smooth_step(controller, scene.frame_current)
        scene.frame_end = max(scene.frame_end, self._settle_end)
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
        layout.label(text=f"Completed steps: {int(controller['step_count'])}")
        layout.prop(controller, '["step_duration_frames"]', text="Motor frames")
        row = layout.row()
        row.enabled = not bool(controller.get("step_busy", False))
        row.operator(ALPHABETS_OT_advance_one.bl_idname, icon="PLAY")
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
