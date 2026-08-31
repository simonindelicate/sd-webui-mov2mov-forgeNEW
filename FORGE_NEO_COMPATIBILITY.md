# Forge Neo compatibility

This fork targets the current [sd-webui-forge-neo][neo] (the `neo` branch of
`Haoming02/sd-webui-forge-classic`) and the Gradio version it supplies —
**Gradio 4.40**. Do not install or downgrade Gradio, PyTorch, or other WebUI
packages for this extension; run it in Forge Neo's own Python environment.

[neo]: https://github.com/Haoming02/sd-webui-forge-classic/tree/neo

## Why this kept breaking

Nearly every failure was a wiring bug at the boundary with the WebUI rather than
a bug in mov2mov itself, and Gradio 4 reports those in a way that points
somewhere other than the cause. Three mechanisms account for most of them:

* **Gradio validates every input against its component's data model** before the
  handler is called. A placeholder component that cannot hold the value pushed
  through it fails inside `preprocess_data`, with a traceback containing only
  Gradio frames.
* **Inputs are matched to values by position.** One extra or missing argument
  does not raise where the mistake is; the values simply shift, and the error
  surfaces on whichever component several positions later happens to be strict.
  A boolean landing on a `gr.Gallery` produces
  `ValidationError: ... GalleryData ... Input should be a valid list`.
* **Forge silently drops keyword arguments Gradio has removed** (with a
  `GradioDeprecationWarning`), so a control can quietly stop honouring a setting
  instead of failing.

The tests in `tests/` now pin all three: `tests/test_ui_construction.py` builds
the whole tab against a stand-in WebUI, and `tests/test_generate_payload.py`
runs a Generate click through the extension's real JavaScript and then through
Gradio's own input validation. Run them with `pytest` from the extension root.

## What changed

### Generate arguments are marshalled by count, not by guesswork

Forge's `create_submit_args()` finds the output values Gradio appends to the
JavaScript arguments by looking for a gallery-shaped array a fixed distance from
the end — correct for txt2img/img2img, whose outputs start with a gallery.
mov2mov's outputs start with a **video**, so that search lands on a script's own
control and truncates real arguments as soon as an extension's last control
holds a list (a checkbox group, a multiselect dropdown, a gallery). Everything
downstream then reads the wrong argument.

`submit_mov2mov()` now takes the declared input count from Python and slices to
it exactly, so the payload cannot drift no matter what extensions are installed
or how Forge's helper changes.

### The hidden placeholder is a Textbox, not a Label

A1111 used `gr.Label(visible=False)` as its throwaway component. Under Gradio 4
`Label` is backed by `LabelData`, so the task id, the tab index and the detected
video resolution — all scalars the JavaScript writes into those slots — fail
validation before mov2mov runs. Forge Neo itself uses `gr.Textbox(visible=False)`
and so does mov2mov now.

### The output gallery is never an event input

mov2mov produces one video, never a gallery of images. The gallery in the result
panel exists only as the surface Forge's `requestProgress()` draws live previews
onto; it holds no value and is now wired into no event at all. The 📂 button
opens the configured output directory and needs no component values, so it takes
none.

### Script arguments are prepared before any section is built

`ScriptRunner.prepare_ui()` resets the runner's argument list, and every control
created afterwards is addressed by the `args_from`/`args_to` slice recorded when
it was created. It used to be called from inside the category loop, so with the
default category order the "prompt" section was already built — and with a
custom `ui_reorder_list` more of them were. Anything created before the reset
kept stale offsets and read another script's arguments. It now runs before the
loop, matching Forge Neo's own `create_ui()`.

### The prompt layout option is Forge Neo's

Forge Neo replaced A1111's `compact_prompt_box` checkbox with a
`prompt_box_style` radio (Default / Compact / Scrollable / Accordion). Reading
the removed option always returned `False`, which happened to render a usable
tab — but in the compact layout `Toprow` defers the generate box until the
output panel calls `create_inline_toprow_image()`, so honouring the setting also
means passing the toprow into the output panel. Both are now done, and all four
layouts are covered by a test.

### Optional settings are read through one accessor

`Options.__getattr__` raises for anything a fork has removed, so every
non-essential setting goes through `scripts/m2m_compat.option()`, which reads the
live value first and falls back to the registered default and then the caller's
default. The same helper reads `shared.cmd_opts`.

### Distilled CFG Scale is exposed

Forge Neo's processing carries `distilled_cfg_scale` for Flux/Chroma-style
models. mov2mov never set it, so every frame used the processing default of 3.5
regardless of what the img2img tab was configured to do. It is now a control
next to CFG Scale, passed through `supported_kwargs()` so the extension still
works on forks that do not have the field.

### Removed backends degrade instead of crashing

Forge Neo ships neither `modules.deepbooru` nor a CLIP interrogator
(`modules/interrogate.py` is gone, so `shared.interrogator` does not exist).
Both keyframe-captioning buttons are detected at build time, disabled with an
explanatory tooltip, and raise a readable `gr.Error` if invoked anyway. Ordinary
mov2mov, custom keyframe prompts and EbSynth do not depend on either.

### Other fixes

* **Modern Gradio component APIs.** Media components select `sources` where the
  installed Gradio supports it (with a `source` fallback), and event updates use
  `gr.update()` rather than the removed per-component `update` methods. The
  keyframe table no longer passes the removed `max_rows`.
* **`IOComponent` is not patched.** The old global monkey patch of
  `gradio.components.IOComponent` is gone — the class no longer exists, and
  patching Gradio globally affected unrelated extensions.
* **The tab builds inside its own `gr.Blocks`.** Forge Neo invokes `on_ui_tabs`
  callbacks while collecting interfaces, outside its root Blocks context, and
  `Toprow` registers events in its constructor.
* **No fake infotext source tab.** Forge's infotext registry has no `mov2mov`
  entry, so registering mov2mov as a paste source made Forge's global
  paste-button pass fail with `KeyError: 'mov2mov'`. The image send buttons do
  not apply to a video-only output panel and are not created.
* **A failed UI callback cannot poison other tabs.** The temporary mov2mov
  script runner is restored in a `finally` block.
* **The JavaScript cannot swallow a click.** A throw inside a frontend function
  rejects the request silently — Generate appears to do nothing — so the DOM
  lookups are null-safe and the progress-bar setup is wrapped.
* **Video validation is explicit.** Invalid or zero source FPS, an invalid
  requested FPS, and a video that decodes to no frames all produce useful errors
  instead of a zero step or an empty output.
* **Saving works.** The download component takes a list, and saving with no
  video yet reports that rather than raising a `TypeError`.

## FaceSwapLab and other always-on scripts

Enable and configure the extension in mov2mov's script section exactly as in
img2img. Mov2mov creates one img2img processing request and replaces its init
image for every sampled video frame, using the same `ScriptRunner` that built
the UI arguments — so img2img always-on scripts receive their normal arguments
and run on every frame. Mov2mov is not an AnimateDiff or generative-video
replacement.

If an always-on extension fails, first confirm that the same settings work on a
single image in Forge Neo's img2img tab. Mov2mov deliberately does not catch and
hide script exceptions: Forge Neo should display the originating extension's
error instead of silently producing an unprocessed video.

## Feature availability

| Feature | Forge Neo behavior |
| --- | --- |
| Frame-by-frame img2img | Enabled |
| Img2img always-on scripts / FaceSwapLab | Enabled |
| Distilled CFG (Flux, Chroma) | Enabled |
| Video rebuilding | Enabled |
| Movie Editor / EbSynth | Enabled on Windows, as before |
| CLIP keyframe captioning | Disabled — Forge Neo has no interrogator |
| Deepbooru keyframe tagging | Disabled — Forge Neo has no `modules.deepbooru` |

Restart Forge Neo after installing or updating the extension. Report startup
errors with the complete console traceback and the Forge Neo commit.
