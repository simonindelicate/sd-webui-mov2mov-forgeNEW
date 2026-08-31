"""Make the extension importable the way the WebUI imports it, and build the tab.

Two things get in the way of a plain `pytest` run: pytest prepends the directory
holding each test module to `sys.path`, so `tests/ebsynth` shadows the
extension's own `ebsynth` package; and the WebUI's `modules` package does not
exist outside an install, so `tests/webui_stub` stands in for it.
"""

import importlib.util
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
STUB = ROOT / "tests" / "webui_stub"

for path in (str(STUB), str(ROOT)):
    while path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)


def _load_package(name, location):
    """Bind ``name`` to a specific directory, immune to later sys.path changes."""
    if name in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(
        name, location / "__init__.py", submodule_search_locations=[str(location)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)


_load_package("ebsynth", ROOT / "ebsynth")


def _webui_install_available():
    """The EbSynth suite resolves ``extensions.sd-webui-mov2mov.tests.utils``."""
    try:
        return importlib.util.find_spec("extensions") is not None
    except (ImportError, ValueError):
        return False


if not _webui_install_available():
    # These tests need a real WebUI checkout (and ebsynth.dll, so Windows) to
    # even import. Everything else in tests/ runs anywhere.
    collect_ignore = ["ebsynth"]


def _install_stub_scripts():
    """Register a script whose controls have the shapes that break the wiring."""
    import gradio as gr

    from modules import scripts as stub_scripts
    from modules.ui_components import InputAccordion

    class AwkwardAlwaysOnScript(stub_scripts.Script):
        """Stands in for a ControlNet-style always-on extension.

        Its last control is list-valued, which is what makes Forge's
        create_submit_args() heuristic truncate mov2mov's arguments, and it owns
        a gallery, which is where a misaligned boolean surfaces as the
        GalleryData validation error.
        """

        alwayson = True
        section = "accordions"

        def title(self):
            return "Awkward"

        def ui(self, is_img2img):
            with InputAccordion(False, label="Awkward", elem_id="awkward_accordion") as enabled:
                gallery = gr.Gallery(label="Reference images", elem_id="awkward_gallery")
                modes = gr.CheckboxGroup(["a", "b"], value=[], elem_id="awkward_modes")
            return [enabled, gallery, modes]

    class SelectableScript(stub_scripts.Script):
        alwayson = False

        def title(self):
            return "Selectable"

        def ui(self, is_img2img):
            return [gr.Slider(label="Amount", elem_id="selectable_amount")]

    stub_scripts.scripts_data[:] = [AwkwardAlwaysOnScript, SelectableScript]


class BuiltTab:
    def __init__(self, interface, label, elem_id, module, gradio_warnings):
        self.interface = interface
        self.label = label
        self.elem_id = elem_id
        self.module = module
        self.gradio_warnings = gradio_warnings


def build_tab():
    from modules.gradio_extensions import GradioDeprecationWarning
    from scripts import m2m_ui

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        interfaces = m2m_ui.on_ui_tabs()

    gradio_warnings = [
        str(entry.message)
        for entry in caught
        if issubclass(entry.category, GradioDeprecationWarning)
    ]

    interface, label, elem_id = interfaces[0]
    return BuiltTab(interface, label, elem_id, m2m_ui, gradio_warnings)


@pytest.fixture(scope="session")
def mov2mov_tab():
    _install_stub_scripts()
    return build_tab()
