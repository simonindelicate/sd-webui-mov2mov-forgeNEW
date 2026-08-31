# WebUI stub

A stand-in for the parts of [sd-webui-forge-neo][neo] that mov2mov builds
against, so the extension's UI can be constructed in a test without a WebUI
install.

Everything here is written from the observable behaviour an extension depends
on — nothing is copied from Forge or A1111. What it deliberately reproduces:

* `gradio_extensions` — the `_js`, `tooltip` and legacy `source` keywords, and
  Forge's habit of warning about and dropping keyword arguments Gradio removed.
* `ui_toprow` — the layout split that decides where the Generate button is
  built, and the constructor-time event registration that forces a tab callback
  to bring its own `gr.Blocks`.
* `scripts` — the `ScriptRunner` argument bookkeeping (`prepare_ui()` resetting
  the input list, `args_from`/`args_to` recorded at control creation), which is
  where argument misalignment originates.
* `shared` — Forge Neo's option set, so reading a setting this fork removed
  raises `AttributeError` here too.

Keep it minimal. It exists to catch wiring mistakes, not to emulate a WebUI.

[neo]: https://github.com/Haoming02/sd-webui-forge-classic/tree/neo
