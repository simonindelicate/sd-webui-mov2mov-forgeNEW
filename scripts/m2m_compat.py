"""Small compatibility helpers for Forge Neo's Gradio stack."""

import inspect

import gradio as gr


def update(**kwargs):
    """Return a component update without relying on removed Component.update APIs."""
    return gr.update(**kwargs)


def option(opts, name, default=None):
    """Read a WebUI option that may not be registered by Forge Neo.

    Forge Neo's ``Options.__getattr__`` raises for A1111 options it has removed.
    Its public ``data`` mapping remains the stable way for extensions to inspect
    optional settings.
    """
    data = getattr(opts, "data", None)
    if isinstance(data, dict):
        return data.get(name, default)
    return getattr(opts, name, default)


def media_source_kwargs(component_class, source="upload"):
    """Use the media source keyword supported by the installed Gradio version."""
    parameters = inspect.signature(component_class.__init__).parameters
    if "sources" in parameters:
        return {"sources": [source]}
    if "source" in parameters:
        return {"source": source}
    return {}
