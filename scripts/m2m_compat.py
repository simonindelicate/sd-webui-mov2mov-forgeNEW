"""Small compatibility helpers for Forge Neo's Gradio stack."""

import inspect

import gradio as gr


def update(**kwargs):
    """Return a component update without relying on removed Component.update APIs."""
    return gr.update(**kwargs)


def media_source_kwargs(component_class, source="upload"):
    """Use the media source keyword supported by the installed Gradio version."""
    parameters = inspect.signature(component_class.__init__).parameters
    if "sources" in parameters:
        return {"sources": [source]}
    if "source" in parameters:
        return {"source": source}
    return {}

