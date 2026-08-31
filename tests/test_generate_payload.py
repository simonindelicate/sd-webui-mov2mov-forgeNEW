"""Run a Generate click end to end: real JavaScript, real Gradio validation.

This is the round trip that kept failing in the browser. The browser hands the
tab's input values plus the current output values to the extension's JavaScript,
whatever comes back becomes the request payload, and Gradio validates it against
each input's data model before mov2mov sees anything. Both halves run here.
"""

import asyncio
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import gradio as gr
import pytest

ROOT = Path(__file__).parents[1]
JAVASCRIPT = ROOT / "javascript" / "m2m_ui.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is required")


def _run_javascript(function_body, tmp_path):
    """Execute the extension's real JavaScript under a stubbed WebUI front end."""
    harness = tmp_path / "harness.js"
    harness.write_text(
        textwrap.dedent(
            """
            // The globals Forge's own scripts provide.
            globalThis.gradioApp = () => ({
                getElementById: () => null,
                querySelector: () => null,
            });
            globalThis.randomId = () => "task(test)";
            globalThis.localSet = () => {};
            globalThis.localRemove = () => {};
            globalThis.showSubmitButtons = () => {};
            globalThis.requestProgress = () => {};
            """
        )
        + JAVASCRIPT.read_text(encoding="utf-8")
        + "\n"
        + function_body,
        encoding="utf-8",
    )

    result = subprocess.run(
        [shutil.which("node"), str(harness)], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def _frontend_value(block):
    """Roughly what Gradio's front end holds as a component's current value."""
    return getattr(block, "value", None)


def _generate_dependency(interface):
    for index, dependency in enumerate(interface.get_config_file()["dependencies"]):
        if "submit_mov2mov" in (dependency.get("js") or ""):
            return index, dependency
    raise AssertionError("the Generate dependency was not found")


@pytest.fixture(scope="module")
def generate_request(mov2mov_tab):
    interface = mov2mov_tab.interface
    index, dependency = _generate_dependency(interface)

    inputs = [_frontend_value(interface.blocks[i]) for i in dependency["inputs"]]
    outputs = [_frontend_value(interface.blocks[i]) for i in dependency["outputs"]]

    return interface, index, dependency, inputs + outputs


def test_forge_create_submit_args_would_corrupt_this_payload(generate_request):
    """Why mov2mov marshals its own arguments.

    Forge's helper finds the appended output values by looking for a
    gallery-shaped array a fixed distance from the end — correct for
    txt2img/img2img, whose outputs start with a gallery. mov2mov's outputs start
    with a video, so the search lands on a script's control instead and takes
    real arguments with it.
    """
    _, _, dependency, browser_args = generate_request

    def create_submit_args(args):  # a transcription of Forge Neo's javascript/ui.js
        res = list(args)
        for offset in (5, 4, 3):
            if isinstance(res[len(res) - offset], list):
                return res[: len(res) - offset]
        return res

    corrupted = create_submit_args(browser_args)
    assert len(corrupted) != len(dependency["inputs"])


def test_the_extension_javascript_returns_exactly_the_declared_inputs(generate_request, tmp_path):
    _, _, dependency, browser_args = generate_request

    marshalled = _run_javascript(
        f"console.log(JSON.stringify(submit_mov2mov({json.dumps(browser_args)}, "
        f"{len(dependency['inputs'])})));",
        tmp_path,
    )

    assert len(marshalled) == len(dependency["inputs"])
    assert marshalled[0] == "task(test)"
    # Everything after the two placeholders is passed through untouched.
    assert marshalled[2:] == browser_args[2 : len(dependency["inputs"])]


def test_gradio_accepts_the_payload_the_javascript_produces(generate_request, tmp_path):
    """The failure the user actually saw was Gradio rejecting an input value.

    Feeding the real marshalled payload through Gradio's own preprocessing is
    the only way to know every component in the tab accepts what it is sent.
    """
    interface, index, dependency, browser_args = generate_request

    marshalled = _run_javascript(
        f"console.log(JSON.stringify(submit_mov2mov({json.dumps(browser_args)}, "
        f"{len(dependency['inputs'])})));",
        tmp_path,
    )

    block_fn = interface.fns[index]
    asyncio.run(interface.preprocess_data(block_fn, marshalled, None))


def test_a_stale_boolean_on_a_gallery_input_is_what_the_traceback_reported(tmp_path):
    """Pins the shape of the reported failure so a regression is recognisable."""
    with pytest.raises(Exception) as reported:
        gr.Gallery.data_model(root=False)

    assert "list" in str(reported.value)
