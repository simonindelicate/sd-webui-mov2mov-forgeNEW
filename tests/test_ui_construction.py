"""Build the mov2mov tab for real, against a stand-in for Forge Neo.

Every crash this extension has hit on Forge Neo showed up either while the tab
was being constructed or on the first click afterwards. Constructing it here —
with a script whose controls have the awkward value shapes (a gallery, a
checkbox group) — catches both classes before they reach a user.

The tab itself is built by the ``mov2mov_tab`` fixture in ``conftest.py``.
"""

import gradio as gr
import pytest


def _dependencies(interface):
    return interface.get_config_file()["dependencies"]


def _component(interface, component_id):
    return interface.blocks[component_id]


def test_the_tab_builds(mov2mov_tab):
    assert isinstance(mov2mov_tab.interface, gr.Blocks)
    assert mov2mov_tab.label == "mov2mov"
    assert mov2mov_tab.elem_id == "mov2mov_tabs"


def test_building_the_tab_reported_no_wiring_errors(mov2mov_tab):
    from modules import errors

    assert errors.reported == []


def test_no_component_is_built_with_arguments_this_gradio_dropped(mov2mov_tab):
    """Forge silently discards keyword arguments Gradio has removed.

    That is what turns "this control no longer does anything" into a bug nobody
    can find: `max_rows`, `source`, `every` and friends just stop applying.
    """
    assert mov2mov_tab.gradio_warnings == []


def test_the_global_script_runner_is_not_left_pointing_at_mov2mov(mov2mov_tab):
    from modules import scripts

    assert scripts.scripts_current is None


def _generate_dependency(interface):
    for dependency in _dependencies(interface):
        js = dependency.get("js") or ""
        if "submit_mov2mov" in js:
            return dependency
    raise AssertionError("the Generate dependency was not found")


def test_generate_declares_the_input_count_its_javascript_slices_to(mov2mov_tab):
    interface = mov2mov_tab.interface
    dependency = _generate_dependency(interface)

    assert f"submit_mov2mov(arguments, {len(dependency['inputs'])})" in dependency["js"]
    assert len(dependency["outputs"]) == 4


def test_no_event_in_the_tab_feeds_a_gallery_as_an_input(mov2mov_tab):
    """A gallery input is only ever correct when something writes to it.

    mov2mov writes a video, so every gallery reachable from this tab is either
    its own empty live-preview surface or a script's. Reading one back is how a
    stray `false` becomes `GalleryData` validation error.
    """
    interface = mov2mov_tab.interface

    offenders = []
    for dependency in _dependencies(interface):
        for component_id in dependency["inputs"]:
            component = _component(interface, component_id)
            if isinstance(component, gr.Gallery) and component.elem_id == "mov2mov_gallery":
                offenders.append(dependency.get("targets"))

    assert offenders == []


def test_the_preview_gallery_is_never_written_to_either(mov2mov_tab):
    interface = mov2mov_tab.interface

    for dependency in _dependencies(interface):
        for component_id in dependency["outputs"]:
            component = _component(interface, component_id)
            assert getattr(component, "elem_id", None) != "mov2mov_gallery"


def test_placeholder_inputs_accept_the_scalars_javascript_writes_into_them(mov2mov_tab):
    """The task id, the tab index and the detected resolution all go through
    hidden placeholder components. Gradio validates them like any other input."""
    interface = mov2mov_tab.interface

    for dependency in _dependencies(interface):
        js = dependency.get("js") or ""
        if "submit_mov2mov" not in js and "currentMov2movSourceResolution" not in js:
            continue
        for component_id in dependency["inputs"]:
            component = _component(interface, component_id)
            if getattr(component, "visible", True):
                continue
            assert not isinstance(component, gr.Label), (
                "gr.Label is backed by LabelData and rejects the scalars these "
                "handlers push through it"
            )


def test_script_arguments_line_up_with_the_declared_inputs(mov2mov_tab):
    """The runner's slices must index into the arguments the UI actually sends."""
    from modules import scripts as stub_scripts

    interface = mov2mov_tab.interface
    dependency = _generate_dependency(interface)

    from scripts.mov2mov import scripts_mov2mov

    custom_inputs = scripts_mov2mov.inputs
    fixed = len(dependency["inputs"]) - len(custom_inputs)
    assert fixed > 0

    input_ids = dependency["inputs"]
    for script in scripts_mov2mov.scripts:
        assert script.args_from is not None
        assert script.args_to <= len(custom_inputs)
        for offset, control in enumerate(custom_inputs[script.args_from : script.args_to]):
            assert input_ids[fixed + script.args_from + offset] == control._id, (
                f"{script.title()} argument {offset} does not point at its own control"
            )


def test_the_source_video_and_the_output_video_are_distinct_components(mov2mov_tab):
    interface = mov2mov_tab.interface
    elem_ids = {
        getattr(block, "elem_id", None)
        for block in interface.blocks.values()
        if isinstance(block, gr.Video)
    }
    assert {"mov2mov_mov", "mov2mov_video"} <= elem_ids


@pytest.mark.parametrize("style", ["Default", "Compact", "Scrollable", "Accordion"])
def test_the_generate_button_exists_in_every_prompt_layout(mov2mov_tab, style):
    """With the compact layout Toprow only renders the generate box when the
    output panel asks for it, so mov2mov has to pass its toprow along."""
    from modules import shared

    m2m_ui = mov2mov_tab.module
    previous = shared.opts.prompt_box_style
    shared.opts.prompt_box_style = style
    try:
        (interface, _, _) = m2m_ui.on_ui_tabs()[0]
    finally:
        shared.opts.prompt_box_style = previous

    elem_ids = {getattr(block, "elem_id", None) for block in interface.blocks.values()}
    assert "mov2mov_generate" in elem_ids
    assert "mov2mov_prompt" in elem_ids


def _button(interface, elem_id):
    for block in interface.blocks.values():
        if getattr(block, "elem_id", None) == elem_id:
            return block
    raise AssertionError(f"{elem_id} not found")


def test_keyframe_captioning_buttons_are_disabled_where_the_backend_is_missing(mov2mov_tab):
    """Forge Neo ships neither modules.deepbooru nor a CLIP interrogator.

    Leaving the buttons live means the user finds out by crashing mid-edit, so
    they are disabled up front and explain themselves in the tooltip.
    """
    interface = mov2mov_tab.interface

    for elem_id in ("mov2mov_video_editor_deepbooru", "mov2mov_video_editor_interrogate"):
        button = _button(interface, elem_id)
        assert button.interactive is False
        assert "Unavailable" in (button.webui_tooltip or "")


def test_keyframe_captioning_raises_a_readable_error_when_invoked_anyway(mov2mov_tab):
    import pandas

    from scripts.movie_editor import MovieEditor

    editor = MovieEditor.__new__(MovieEditor)
    frame = pandas.DataFrame([{"id": 0, "frame": 1, "prompt": ""}])

    for handler in (editor.deepbooru_keyframe, editor.interrogate_keyframe):
        with pytest.raises(gr.Error) as raised:
            handler(frame)
        assert "unavailable" in str(raised.value).lower()
