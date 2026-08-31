"""Regression tests for the Forge Neo / Gradio 4 integration.

The failures this extension keeps hitting are not logic bugs inside mov2mov;
they are wiring bugs at the boundary with the WebUI: a placeholder component
Gradio 4 refuses to validate, an argument list that drifts out of sync with the
handler, a Gradio value shape that changed. These tests pin the wiring.
"""

import ast
import sys
import types
from pathlib import Path

import gradio as gr
import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _module(name):
    return ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))


def _function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name}() not found")


def _calls(node, name):
    """Every call to ``name`` or ``<something>.name`` under ``node``."""
    found = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == name:
            found.append(child)
        elif isinstance(func, ast.Name) and func.id == name:
            found.append(child)
    return found


def _keyword(call, name):
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


# --------------------------------------------------------------------------- #
# Gradio 4 component contracts
# --------------------------------------------------------------------------- #


def test_gradio_rejects_scalars_pushed_through_a_label_placeholder():
    """Why the hidden placeholder may not be a gr.Label.

    A1111 used gr.Label as its throwaway component. Under Gradio 4 a Label is
    backed by LabelData, so the task id and the resolution numbers the JS
    helpers write into those slots fail validation before mov2mov is ever
    called. A Textbox takes them.
    """
    assert gr.Label.data_model is not None
    with pytest.raises(Exception):
        gr.Label.data_model(**"task(abc)")

    assert gr.Textbox().preprocess("task(abc)") == "task(abc)"


def test_gallery_inputs_reject_non_list_values():
    """Why no mov2mov event may take the output gallery as an input.

    mov2mov's gallery is only a live-preview surface and never holds a value.
    Any non-list that reaches it — a stale `false`, a misaligned checkbox — is a
    hard validation error inside Gradio, before any mov2mov code runs.
    """
    with pytest.raises(Exception):
        gr.Gallery.data_model(root=False)


def test_video_component_accepts_the_source_keyword_this_gradio_supports():
    sys.path.insert(0, str(ROOT))
    try:
        from scripts.m2m_compat import media_source_kwargs
    finally:
        sys.path.pop(0)

    kwargs = media_source_kwargs(gr.Video)
    assert kwargs in ({"sources": ["upload"]}, {"source": "upload"})
    gr.Video(**kwargs)


# --------------------------------------------------------------------------- #
# Option compatibility
# --------------------------------------------------------------------------- #


@pytest.fixture()
def compat():
    sys.path.insert(0, str(ROOT))
    try:
        from scripts import m2m_compat

        return m2m_compat
    finally:
        sys.path.pop(0)


class _ForgeOptions:
    """Stands in for Forge Neo's Options: unknown names raise AttributeError."""

    def __init__(self, values):
        self.data = dict(values)

    def __getattr__(self, item):
        if item == "data":
            raise AttributeError(item)
        try:
            return self.data[item]
        except KeyError:
            raise AttributeError(item) from None


def test_option_prefers_the_live_value_over_the_fallback(compat):
    opts = _ForgeOptions({"gallery_height": "768px"})
    assert compat.option(opts, "gallery_height", "") == "768px"


def test_option_returns_the_fallback_for_settings_this_fork_removed(compat):
    opts = _ForgeOptions({})
    assert compat.option(opts, "compact_prompt_box", False) is False
    assert compat.option(opts, "open_dir_button_choice", "") == ""


def test_option_reads_argparse_namespaces(compat):
    assert compat.option(types.SimpleNamespace(hide_ui_dir_config=True), "hide_ui_dir_config", False) is True
    assert compat.option(types.SimpleNamespace(), "hide_ui_dir_config", False) is False


def test_toprow_compact_follows_forge_neos_prompt_box_style(compat):
    assert compat.toprow_is_compact(_ForgeOptions({"prompt_box_style": "Compact"})) is True
    assert compat.toprow_is_compact(_ForgeOptions({"prompt_box_style": "Default"})) is False
    # A1111 and older Forge releases, which still have the checkbox.
    assert compat.toprow_is_compact(_ForgeOptions({"compact_prompt_box": True})) is True


def test_supported_kwargs_drops_fields_this_fork_does_not_have(compat):
    def forge_neo(cfg_scale=None, distilled_cfg_scale=None):
        pass

    def a1111(cfg_scale=None):
        pass

    assert compat.supported_kwargs(forge_neo, distilled_cfg_scale=3.5) == {"distilled_cfg_scale": 3.5}
    assert compat.supported_kwargs(a1111, distilled_cfg_scale=3.5) == {}


# --------------------------------------------------------------------------- #
# Generate wiring
# --------------------------------------------------------------------------- #


def _fixed_input_count():
    tree = _module("m2m_ui.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "fixed_inputs" for t in node.targets
        ):
            assert isinstance(node.value, ast.List)
            return len(node.value.elts)
    raise AssertionError("fixed_inputs list not found in m2m_ui.py")


def _handler_parameter_count():
    handler = _function(_module("mov2mov.py"), "mov2mov")
    count = 0
    for argument in handler.args.args:
        annotation = argument.annotation
        # gradio injects gr.Request itself; the UI does not supply it.
        if isinstance(annotation, ast.Attribute) and annotation.attr == "Request":
            continue
        count += 1
    assert handler.args.vararg is not None, "mov2mov() must keep its *args for script arguments"
    return count


def test_the_ui_passes_exactly_the_arguments_mov2mov_declares():
    """The single most damaging failure mode: a silent off-by-one.

    Gradio maps payload values to inputs by position, so one extra or missing
    argument does not raise where the mistake is; it lands a checkbox on a
    gallery or a number on a dataframe several controls later.
    """
    assert _fixed_input_count() == _handler_parameter_count()


def test_generate_marshals_its_own_arguments_by_count():
    """Forge's create_submit_args() guesses; mov2mov must not rely on the guess.

    It locates the appended output values by looking for a gallery-shaped array
    at a fixed offset from the end. mov2mov's outputs start with a video, so the
    guess misfires as soon as a script's last control holds a list.
    """
    ui = (SCRIPTS / "m2m_ui.py").read_text(encoding="utf-8")
    javascript = (ROOT / "javascript" / "m2m_ui.js").read_text(encoding="utf-8")
    code = "\n".join(
        line for line in javascript.splitlines() if not line.lstrip().startswith(("*", "//", "/*"))
    )

    assert "create_submit_args" not in code
    assert "submit_mov2mov(arguments, {len(mov2mov_inputs)})" in ui
    assert "function submit_mov2mov(args, inputCount)" in javascript
    assert "slice(0, inputCount)" in javascript


def test_generate_outputs_match_the_error_path_placeholders():
    """wrap_gradio_gpu_call appends an error HTML value to extra_outputs."""
    build = _function(_module("m2m_ui.py"), "_build_ui_tabs")

    (call,) = [c for c in _calls(build, "dict") if _calls(c, "wrap_gradio_gpu_call")]
    outputs = _keyword(call, "outputs")
    assert isinstance(outputs, ast.List)

    (wrapper,) = _calls(call, "wrap_gradio_gpu_call")
    extra_outputs = _keyword(wrapper, "extra_outputs")
    assert len(extra_outputs.elts) + 1 == len(outputs.elts)


def test_script_arguments_are_prepared_before_any_section_is_built():
    """prepare_ui() resets the runner's argument list.

    Categories are rendered in a user-configurable order, so anything built
    before prepare_ui() would keep stale args_from/args_to offsets and every
    script downstream of it would read the wrong slice.
    """
    build = _function(_module("m2m_ui.py"), "_build_ui_tabs")

    prepare = _calls(build, "prepare_ui")
    assert len(prepare) == 1

    loops = [n for n in ast.walk(build) if isinstance(n, ast.For)]
    category_loops = [
        n for n in loops if isinstance(n.target, ast.Name) and n.target.id == "category"
    ]
    assert len(category_loops) == 1
    assert prepare[0].lineno < category_loops[0].lineno


def test_setup_ui_is_called_once_per_category():
    build = _function(_module("m2m_ui.py"), "_build_ui_tabs")
    assert len(_calls(build, "setup_ui")) == 1
    # One inside the "accordions" branch, one for every other category.
    assert len(_calls(build, "setup_ui_for_section")) == 2


# --------------------------------------------------------------------------- #
# Output panel
# --------------------------------------------------------------------------- #


def test_no_event_takes_the_preview_gallery_as_an_input():
    panel = _function(_module("m2m_ui_common.py"), "create_output_panel")

    for click in _calls(panel, "click"):
        inputs = _keyword(click, "inputs")
        if inputs is None:
            continue
        names = ast.dump(inputs)
        assert "gallery" not in names, ast.unparse(click)


def test_output_panel_renders_the_inline_generate_box():
    """With the compact prompt layout, Toprow defers the generate box to here."""
    ui = (SCRIPTS / "m2m_ui.py").read_text(encoding="utf-8")
    panel = (SCRIPTS / "m2m_ui_common.py").read_text(encoding="utf-8")

    assert "create_inline_toprow_image()" in panel
    assert "def create_output_panel(tabname, outdir, toprow=None)" in panel
    build = _function(ast.parse(ui), "_build_ui_tabs")
    (call,) = _calls(build, "create_output_panel")
    assert any(isinstance(a, ast.Name) and a.id == "toprow" for a in call.args)


def test_saving_a_video_returns_a_list_for_the_multi_file_download():
    common = (SCRIPTS / "m2m_ui_common.py").read_text(encoding="utf-8")
    assert 'file_count="multiple"' in common
    assert "update(value=[video_path], visible=True)" in common


# --------------------------------------------------------------------------- #
# Removed / renamed WebUI APIs
# --------------------------------------------------------------------------- #


def test_removed_gradio_apis_are_not_used_by_runtime_code():
    runtime = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SCRIPTS.glob("*.py")
        if path.name != "module_ui_extensions.py"
    )
    assert "gradio.components.IOComponent" not in runtime
    assert "gr.Image.update(" not in runtime
    assert "gr.Slider.update(" not in runtime
    assert "gr.File.update(" not in runtime
    assert "gr.Label(" not in runtime


def test_deepbooru_is_not_a_required_modules_import():
    editor = (SCRIPTS / "movie_editor.py").read_text(encoding="utf-8")
    assert "from modules import shared, deepbooru" not in editor
    assert "except ImportError:" in editor


def test_processing_uses_the_matching_script_runner():
    processing = (SCRIPTS / "mov2mov.py").read_text(encoding="utf-8")
    assert "p.scripts = scripts_mov2mov" in processing


def test_optional_webui_settings_go_through_the_compatibility_accessor():
    runtime = "\n".join(
        (SCRIPTS / name).read_text(encoding="utf-8")
        for name in ("m2m_ui.py", "m2m_ui_common.py", "mov2mov.py", "movie_editor.py")
    )
    unsupported_direct_accesses = (
        "shared.opts.gallery_height",
        "shared.opts.open_dir_button_choice",
        "shared.opts.outdir_save",
        "shared.opts.outdir_samples",
        "shared.opts.enable_console_prompts",
        "shared.opts.compact_prompt_box",
        "shared.opts.prompt_box_style",
        "opts.samples_log_stdout",
        "opts.do_not_show_images",
        "shared.cmd_opts.hide_ui_dir_config",
        "shared.opts.data.get(",
    )
    for access in unsupported_direct_accesses:
        assert access not in runtime, access


def test_ui_callback_restores_the_global_script_runner():
    ui = (SCRIPTS / "m2m_ui.py").read_text(encoding="utf-8")
    assert "previous_runner = scripts.scripts_current" in ui
    assert "scripts.scripts_current = previous_runner" in ui


def test_tab_is_built_inside_its_own_blocks():
    """Forge Neo calls on_ui_tabs outside its root Blocks context."""
    ui = (SCRIPTS / "m2m_ui.py").read_text(encoding="utf-8")
    blocks = ui.index("as mov2mov_interface:")
    toprow = ui.index("toprow = ui_toprow.Toprow(")
    callback_return = ui.index('return [(mov2mov_interface, "mov2mov"')
    assert blocks < toprow < callback_return
    assert "with gr.TabItem(" not in ui
    assert 'elem_id="txt2img_extra_tabs"' not in ui


def test_mov2mov_does_not_register_unknown_infotext_source_tab():
    """Forge's global paste-button pass raises KeyError for unknown source tabs."""
    output_ui = (SCRIPTS / "m2m_ui_common.py").read_text(encoding="utf-8")
    assert "register_paste_params_button" not in output_ui
    assert "ParamBinding" not in output_ui
    assert "source_tabname" not in output_ui
    assert "modules.infotext_utils" not in output_ui


def test_javascript_helpers_tolerate_missing_elements():
    javascript = (ROOT / "javascript" / "m2m_ui.js").read_text(encoding="utf-8")
    # A throw inside the frontend function rejects the request silently, which
    # looks to the user like Generate doing nothing at all.
    assert "if (video) video.style.display" in javascript
    assert "if (gallery) gallery.style.display" in javascript
    assert "catch (error)" in javascript
