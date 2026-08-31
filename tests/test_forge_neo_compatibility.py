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
