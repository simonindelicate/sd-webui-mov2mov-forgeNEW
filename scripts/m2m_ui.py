import inspect
from contextlib import ExitStack

import gradio as gr

from modules import (
    errors,
    script_callbacks,
    scripts,
    shared,
    ui_toprow,
)
from modules.call_queue import wrap_gradio_gpu_call
from modules.shared import opts
from modules.ui import (
    create_override_settings_dropdown,
    detect_image_size_symbol,
    ordered_ui_categories,
    resize_from_to_html,
    switch_values_symbol,
)
from modules.ui_components import (
    FormGroup,
    FormHTML,
    FormRow,
    ResizeHandleRow,
    ToolButton,
)
from scripts import mov2mov
from scripts.m2m_compat import media_source_kwargs, option, toprow_is_compact
from scripts.m2m_config import mov2mov_output_dir, mov2mov_outpath_samples
from scripts.m2m_ui_common import create_output_panel
from scripts.mov2mov import scripts_mov2mov
from scripts.movie_editor import MovieEditor

id_part = "mov2mov"


def on_ui_settings():
    section = ("mov2mov", "Mov2Mov")
    shared.opts.add_option(
        "mov2mov_outpath_samples",
        shared.OptionInfo(
            mov2mov_outpath_samples, "Mov2Mov output path for image", section=section
        ),
    )
    shared.opts.add_option(
        "mov2mov_output_dir",
        shared.OptionInfo(
            mov2mov_output_dir, "Mov2Mov output path for video", section=section
        ),
    )


def _fixed_parameter_count(fn):
    """Positional parameters ``fn`` takes before its ``*args`` catch-all.

    ``gradio`` injects the ``gr.Request`` parameter itself, so it is not supplied
    by the UI and must not be counted.
    """
    count = 0
    for parameter in inspect.signature(fn).parameters.values():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            break
        if parameter.annotation is gr.Request:
            continue
        count += 1
    return count


def _check_input_count(fn, fixed_inputs):
    """Fail loudly at build time if the UI and the handler have drifted apart.

    An off-by-one here does not raise on the Python side: Gradio simply feeds
    every value to the wrong component and reports it as a validation error on
    whichever input happens to be strict (a checkbox landing on a gallery, say).
    Catching it while the tab is built keeps that class of bug legible.
    """
    expected = _fixed_parameter_count(fn)
    if len(fixed_inputs) != expected:
        errors.report(
            f"mov2mov: UI passes {len(fixed_inputs)} fixed arguments but "
            f"{fn.__name__}() declares {expected}. Script arguments will be "
            "misaligned; this is a bug in the extension.",
            exc_info=False,
        )


def _build_ui_tabs():
    """Construct the mov2mov tab.

    ``on_ui_tabs`` callbacks run while Forge Neo is collecting interfaces, not
    from inside its root Blocks context, so the tab has to bring its own
    ``gr.Blocks`` (Toprow registers events in its constructor).
    """
    scripts.scripts_current = scripts_mov2mov
    scripts_mov2mov.initialize_scripts(is_img2img=True)

    with gr.Blocks(analytics_enabled=False) as mov2mov_interface:
        toprow = ui_toprow.Toprow(
            is_img2img=True,
            is_compact=toprow_is_compact(shared.opts),
            id_part=id_part,
        )

        # Gradio 4 validates every input against its component's data model, so
        # a placeholder must be a component that accepts a scalar. gr.Label is
        # backed by LabelData and rejects the task id and the resolution numbers
        # the JavaScript helpers push through these slots.
        dummy_component = gr.Textbox(visible=False)

        extra_tabs = gr.Tabs(
            elem_id=f"{id_part}_extra_tabs", elem_classes=["extra-networks"]
        )
        extra_tabs.__enter__()

        with gr.Tab(
            "Generation", id=f"{id_part}_generation"
        ) as mov2mov_generation_tab, ResizeHandleRow(equal_height=False):

            with ExitStack() as stack:
                stack.enter_context(
                    gr.Column(variant="compact", elem_id=f"{id_part}_settings")
                )

                # Must run before any setup_ui_for_section() call: prepare_ui()
                # resets the runner's argument list, and every control created
                # before it would keep stale args_from/args_to offsets. The
                # category order is user configurable, so "image" is not
                # reliably first.
                scripts_mov2mov.prepare_ui()

                for category in ordered_ui_categories():

                    if category == "prompt":
                        toprow.create_inline_toprow_prompts()

                    if category == "image":
                        init_mov = gr.Video(
                            label="Video for mov2mov",
                            elem_id=f"{id_part}_mov",
                            show_label=False,
                            **media_source_kwargs(gr.Video),
                        )

                        with FormRow():
                            resize_mode = gr.Radio(
                                label="Resize mode",
                                elem_id=f"{id_part}_resize_mode",
                                choices=[
                                    "Just resize",
                                    "Crop and resize",
                                    "Resize and fill",
                                    "Just resize (latent upscale)",
                                ],
                                type="index",
                                value="Just resize",
                            )

                    elif category == "dimensions":
                        with FormRow():
                            with gr.Column(elem_id=f"{id_part}_column_size", scale=4):
                                selected_scale_tab = gr.Number(value=0, visible=False)
                                with gr.Tabs(elem_id=f"{id_part}_tabs_resize"):
                                    with gr.Tab(
                                        label="Resize to",
                                        id="to",
                                        elem_id=f"{id_part}_tab_resize_to",
                                    ) as tab_scale_to:
                                        with FormRow():
                                            with gr.Column(
                                                elem_id=f"{id_part}_resize_to_column",
                                                scale=4,
                                            ):
                                                width = gr.Slider(
                                                    minimum=64,
                                                    maximum=2048,
                                                    step=8,
                                                    label="Width",
                                                    value=512,
                                                    elem_id=f"{id_part}_width",
                                                )
                                                height = gr.Slider(
                                                    minimum=64,
                                                    maximum=2048,
                                                    step=8,
                                                    label="Height",
                                                    value=512,
                                                    elem_id=f"{id_part}_height",
                                                )

                                            with gr.Column(
                                                elem_id=f"{id_part}_dimensions_row",
                                                scale=1,
                                                elem_classes="dimensions-tools",
                                            ):
                                                res_switch_btn = ToolButton(
                                                    value=switch_values_symbol,
                                                    elem_id=f"{id_part}_res_switch_btn",
                                                    tooltip="Switch width/height",
                                                )
                                                detect_image_size_btn = ToolButton(
                                                    value=detect_image_size_symbol,
                                                    elem_id=f"{id_part}_detect_image_size_btn",
                                                    tooltip="Auto detect size from the source video",
                                                )

                                    with gr.Tab(
                                        label="Resize by",
                                        id="by",
                                        elem_id=f"{id_part}_tab_resize_by",
                                    ) as tab_scale_by:
                                        scale_by = gr.Slider(
                                            minimum=0.05,
                                            maximum=4.0,
                                            step=0.05,
                                            label="Scale",
                                            value=1.0,
                                            elem_id=f"{id_part}_scale",
                                        )

                                        with FormRow():
                                            scale_by_html = FormHTML(
                                                resize_from_to_html(0, 0, 0.0),
                                                elem_id=f"{id_part}_scale_resolution_preview",
                                            )
                                            gr.Slider(
                                                label="Unused",
                                                elem_id=f"{id_part}_unused_scale_by_slider",
                                            )
                                            button_update_resize_to = gr.Button(
                                                visible=False,
                                                elem_id=f"{id_part}_update_resize_to",
                                            )

                                    on_change_args = dict(
                                        fn=_resize_from_to_html,
                                        _js="currentMov2movSourceResolution",
                                        inputs=[
                                            dummy_component,
                                            dummy_component,
                                            scale_by,
                                        ],
                                        outputs=scale_by_html,
                                        show_progress=False,
                                    )

                                    scale_by.release(**on_change_args)
                                    button_update_resize_to.click(**on_change_args)

                                tab_scale_to.select(
                                    fn=lambda: 0,
                                    inputs=[],
                                    outputs=[selected_scale_tab],
                                )
                                tab_scale_by.select(
                                    fn=lambda: 1,
                                    inputs=[],
                                    outputs=[selected_scale_tab],
                                )

                    elif category == "denoising":
                        denoising_strength = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            step=0.01,
                            label="Denoising strength",
                            value=0.75,
                            elem_id=f"{id_part}_denoising_strength",
                        )
                        noise_multiplier = gr.Slider(
                            minimum=0,
                            maximum=1.5,
                            step=0.01,
                            label="Noise multiplier",
                            elem_id=f"{id_part}_noise_multiplier",
                            value=1,
                        )
                        with gr.Row(elem_id=f"{id_part}_frames_setting"):
                            movie_frames = gr.Slider(
                                minimum=1,
                                maximum=60,
                                step=1,
                                label="Movie FPS",
                                elem_id=f"{id_part}_movie_frames",
                                value=30,
                            )
                            max_frames = gr.Number(
                                label="Max frames (-1 for all)",
                                value=-1,
                                elem_id=f"{id_part}_max_frames",
                            )

                    elif category == "cfg":
                        with gr.Row():
                            cfg_scale = gr.Slider(
                                minimum=1.0,
                                maximum=30.0,
                                step=0.5,
                                label="CFG Scale",
                                value=7.0,
                                elem_id=f"{id_part}_cfg_scale",
                            )
                            # Forge Neo needs this for distilled models (Flux,
                            # Chroma); without it every frame silently uses the
                            # processing default.
                            distilled_cfg_scale = gr.Slider(
                                minimum=0.0,
                                maximum=24.0,
                                step=0.5,
                                label="Distilled CFG Scale",
                                value=3.5,
                                elem_id=f"{id_part}_distilled_cfg_scale",
                            )
                            image_cfg_scale = gr.Slider(
                                minimum=0,
                                maximum=3.0,
                                step=0.05,
                                label="Image CFG Scale",
                                value=1.5,
                                elem_id=f"{id_part}_image_cfg_scale",
                                visible=False,
                            )

                    elif category == "checkboxes":
                        with FormRow(elem_classes="checkboxes-row", variant="compact"):
                            pass

                    elif category == "accordions":
                        with gr.Row(
                            elem_id=f"{id_part}_accordions", elem_classes="accordions"
                        ):
                            scripts_mov2mov.setup_ui_for_section(category)

                    elif category == "override_settings":
                        with FormRow(elem_id=f"{id_part}_override_settings_row") as row:
                            override_settings = create_override_settings_dropdown(
                                id_part, row
                            )

                    elif category == "scripts":
                        editor = MovieEditor(id_part, init_mov, movie_frames)
                        editor.render()
                        with FormGroup(elem_id=f"{id_part}_script_container"):
                            custom_inputs = scripts_mov2mov.setup_ui()

                    if category not in {"accordions"}:
                        scripts_mov2mov.setup_ui_for_section(category)

            output_panel = create_output_panel(
                id_part,
                option(opts, "mov2mov_output_dir", mov2mov_output_dir),
                toprow,
            )

            fixed_inputs = [
                dummy_component,  # replaced by the task id in JavaScript
                dummy_component,  # replaced by the tab index in JavaScript
                toprow.prompt,
                toprow.negative_prompt,
                toprow.ui_styles.dropdown,
                init_mov,
                cfg_scale,
                distilled_cfg_scale,
                image_cfg_scale,
                denoising_strength,
                selected_scale_tab,
                height,
                width,
                scale_by,
                resize_mode,
                override_settings,
                # mov2mov params
                noise_multiplier,
                movie_frames,
                max_frames,
                # editor
                editor.gr_enable_movie_editor,
                editor.gr_df,
                editor.gr_eb_weight,
            ]
            _check_input_count(mov2mov.mov2mov, fixed_inputs)

            mov2mov_inputs = fixed_inputs + custom_inputs

            # Forge Neo's create_submit_args() guesses where the appended output
            # values start by looking for a gallery-shaped array at a fixed
            # offset. mov2mov's outputs begin with a video, so that guess is
            # wrong here and truncates real arguments as soon as a script's last
            # control happens to hold a list. Pass the exact count instead.
            mov2mov_args = dict(
                fn=wrap_gradio_gpu_call(mov2mov.mov2mov, extra_outputs=[None, "", ""]),
                _js=f"function(){{ return submit_mov2mov(arguments, {len(mov2mov_inputs)}) }}",
                inputs=mov2mov_inputs,
                outputs=[
                    output_panel.video,
                    output_panel.generation_info,
                    output_panel.infotext,
                    output_panel.html_log,
                ],
                show_progress=False,
            )

            toprow.prompt.submit(**mov2mov_args)
            toprow.submit.click(**mov2mov_args)

            res_switch_btn.click(
                fn=lambda w, h: (h, w),
                inputs=[width, height],
                outputs=[width, height],
                show_progress=False,
            )
            detect_image_size_btn.click(
                fn=_detect_image_size,
                _js="currentMov2movSourceResolution",
                inputs=[dummy_component, dummy_component, dummy_component],
                outputs=[width, height],
                show_progress=False,
            )

        extra_tabs.__exit__()

    return [(mov2mov_interface, "mov2mov", f"{id_part}_tabs")]


def _to_number(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _resize_from_to_html(width, height, scale_by):
    """Wrap Forge's helper so the placeholder's string values cannot break it."""
    return resize_from_to_html(_to_number(width), _to_number(height), scale_by or 0.0)


def _detect_image_size(width, height, _unused):
    # The placeholder is a Textbox, so "0" arrives truthy; compare numerically.
    width = _to_number(width)
    height = _to_number(height)
    return (width or gr.update(), height or gr.update())


def on_ui_tabs():
    """Build the tab without leaking mov2mov's runner into other UI callbacks."""
    previous_runner = scripts.scripts_current
    try:
        return _build_ui_tabs()
    finally:
        # UI construction can fail when another extension has incompatible UI
        # code. Always restore Forge's global runner so txt2img/img2img startup
        # is not poisoned by a mov2mov callback error.
        scripts.scripts_current = previous_runner


script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)
