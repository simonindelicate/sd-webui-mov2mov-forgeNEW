# Forge Neo compatibility

This fork targets the current `sd-webui-forge-neo` and the Gradio version that
Forge Neo supplies. Do not install or downgrade Gradio, PyTorch, or other WebUI
packages for this extension.

## What changed

* **Normal img2img execution is preserved.** Each decoded frame is assigned to
  `StableDiffusionProcessingImg2Img.init_images` and sent through
  `process_images`. The processing object and UI arguments now use the same
  mov2mov `ScriptRunner`. Consequently img2img always-on scripts—including
  FaceSwapLab—receive their normal arguments and run on every frame. Mov2mov is
  not an AnimateDiff or generative-video replacement.
* **Deepbooru is optional.** Forge Neo no longer ships `modules.deepbooru`.
  Movie Editor therefore imports it optionally, disables only the Deepbooru
  button when absent, and reports a clear error if its handler is invoked. CLIP
  interrogation, custom prompts, keyframes, ordinary mov2mov, and EbSynth remain
  independent of it.
* **Modern Gradio component APIs are used.** Media components select `sources`
  on modern Gradio (while retaining a `source` fallback), and event updates use
  `gr.update()` rather than removed per-component `Image.update`,
  `Slider.update`, and `File.update` methods.
* **The removed `IOComponent` is not patched.** The old global monkey patch of
  `gradio.components.IOComponent` has been retired. Duplicate element IDs were
  fixed locally instead, avoiding changes to Gradio or other extensions.
* **UI registration uses Forge callbacks.** The mov2mov tab is registered with
  `script_callbacks.on_ui_tabs`, rather than monkey-patching Gradio's private
  `BlockContext.__init__`. Output wiring includes generation info, matching the
  four values returned by the generation function. The callback constructs and
  returns its own `gr.Blocks` interface; Forge Neo invokes tab callbacks outside
  its root Blocks context, and Toprow registers image-prompt events during its
  constructor.
* **Removed WebUI options have local defaults.** Forge Neo does not register
  A1111's `compact_prompt_box` option. Mov2mov reads optional settings through
  the options data mapping and defaults this UI preference to `False`, avoiding
  a tab callback failure without adding the removed option back to Forge Neo.
  The same guarded access is used for nonessential gallery, output-directory,
  logging, and console options that differ among A1111 and Forge Neo releases.
* **Failed UI callbacks do not affect other tabs.** The temporary mov2mov script
  runner is restored in a `finally` block. If mov2mov or another extension raises
  while constructing the UI, Forge Neo's later txt2img/img2img callbacks do not
  inherit mov2mov's global runner.
* **Mov2mov does not register a fake infotext source tab.** Forge Neo's infotext
  registry contains built-in sources such as `txt2img` and `img2img`, but there
  is no `mov2mov` entry. The old image-gallery send buttons registered mov2mov as
  a source and caused Forge's global paste-button connection pass to fail with
  `KeyError: 'mov2mov'`. Those inapplicable image send bindings are not created
  for a video-only output panel.
* **Video validation is explicit.** Invalid/zero source FPS and invalid requested
  FPS now produce useful errors, and frame sampling can no longer calculate a
  zero step.

## FaceSwapLab and other always-on scripts

Enable and configure the extension in mov2mov's script section exactly as in
img2img. Mov2mov creates one img2img processing request and replaces its init
image for every sampled video frame. The runner invokes selectable and always-on
img2img scripts using their mov2mov UI arguments before the result is encoded
back into a video.

If an always-on extension fails, first confirm that the same settings work on a
single image in Forge Neo's img2img tab. Mov2mov deliberately does not catch and
hide script exceptions: Forge Neo should display the originating extension's
error instead of silently producing an unprocessed video.

## Feature availability

| Feature | Forge Neo behavior |
| --- | --- |
| Frame-by-frame img2img | Enabled |
| Img2img always-on scripts / FaceSwapLab | Enabled |
| Video rebuilding | Enabled |
| Movie Editor / EbSynth | Enabled on Windows, as before |
| CLIP keyframe interrogation | Enabled when Forge's interrogator is available |
| Deepbooru keyframe tagging | Disabled when `modules.deepbooru` is absent |

Restart Forge Neo after installing or updating the extension. Startup errors
should be reported with the complete console traceback and Forge Neo commit;
the extension must run in Forge Neo's own Python environment.
