from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_removed_gradio_apis_are_not_used_by_runtime_code():
    runtime = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts").glob("*.py")
        if path.name != "module_ui_extensions.py"
    )
    assert "gradio.components.IOComponent" not in runtime
    assert "gr.Image.update(" not in runtime
    assert "gr.Slider.update(" not in runtime
    assert "gr.File.update(" not in runtime


def test_deepbooru_is_not_a_required_modules_import():
    editor = (ROOT / "scripts" / "movie_editor.py").read_text(encoding="utf-8")
    assert "from modules import shared, deepbooru" not in editor
    assert "except ImportError:" in editor


def test_processing_uses_the_matching_script_runner():
    processing = (ROOT / "scripts" / "mov2mov.py").read_text(encoding="utf-8")
    assert "p.scripts = scripts_mov2mov" in processing


def test_removed_compact_prompt_option_is_read_with_a_fallback():
    ui = (ROOT / "scripts" / "m2m_ui.py").read_text(encoding="utf-8")
    assert 'option(shared.opts, "compact_prompt_box", False)' in ui
    assert "shared.opts.compact_prompt_box" not in ui


def test_all_optional_webui_settings_use_compatibility_accessor():
    runtime = "\n".join(
        (ROOT / "scripts" / name).read_text(encoding="utf-8")
        for name in ("m2m_ui.py", "m2m_ui_common.py", "mov2mov.py")
    )
    unsupported_direct_accesses = (
        "shared.opts.gallery_height",
        "shared.opts.open_dir_button_choice",
        "shared.opts.outdir_save",
        "shared.opts.outdir_samples",
        "shared.opts.enable_console_prompts",
        "opts.samples_log_stdout",
        "opts.do_not_show_images",
        "shared.cmd_opts.hide_ui_dir_config",
    )
    for access in unsupported_direct_accesses:
        assert access not in runtime


def test_ui_callback_restores_the_global_script_runner():
    ui = (ROOT / "scripts" / "m2m_ui.py").read_text(encoding="utf-8")
    assert "previous_runner = scripts.scripts_current" in ui
    assert "scripts.scripts_current = previous_runner" in ui


def test_toprow_is_created_inside_a_blocks_context():
    ui = (ROOT / "scripts" / "m2m_ui.py").read_text(encoding="utf-8")
    blocks = ui.index("with gr.Blocks() as mov2mov_interface:")
    toprow = ui.index("toprow = ui_toprow.Toprow(")
    callback_return = ui.index('return [(mov2mov_interface, "mov2mov"')
    assert blocks < toprow < callback_return
    assert "with gr.TabItem(" not in ui
    assert 'elem_id="txt2img_extra_tabs"' not in ui
    assert 'elem_id="resize_mode"' not in ui


def test_mov2mov_does_not_register_unknown_infotext_source_tab():
    output_ui = (ROOT / "scripts" / "m2m_ui_common.py").read_text(
        encoding="utf-8"
    )
    assert "register_paste_params_button" not in output_ui
    assert "ParamBinding" not in output_ui
    assert "source_tabname" not in output_ui
    assert "modules.infotext_utils" not in output_ui
