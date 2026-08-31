"""Legacy module retained so upgrades do not leave a crashing script behind.

Older releases monkey-patched ``gradio.components.IOComponent`` from here to
work around duplicate element IDs. IOComponent was removed by modern Gradio and
patching Gradio globally could also affect unrelated extensions. Mov2mov now uses
unique IDs at their declarations, so no runtime patch is necessary.
"""
