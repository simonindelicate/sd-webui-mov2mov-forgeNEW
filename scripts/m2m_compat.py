"""Compatibility helpers for the Forge Neo / Gradio 4 stack.

Forge Neo tracks upstream A1111 loosely: options get renamed or dropped, and the
bundled Gradio (4.40) is stricter than the Gradio 3 this extension was written
for.  Everything in this module exists so the rest of mov2mov can ask for
something without having to know which fork or Gradio version is installed.
"""

import inspect
from collections.abc import Mapping

import gradio as gr

_MISSING = object()


def update(**kwargs):
    """Return a component update without relying on removed Component.update APIs."""
    return gr.update(**kwargs)


def option(opts, name, default=None):
    """Read a WebUI option / command line flag that this fork may not define.

    Forge Neo drops A1111 options (``compact_prompt_box``) and adds its own
    (``prompt_box_style``).  ``Options.__getattr__`` raises ``AttributeError``
    for anything it does not know, so a plain attribute read is unsafe. Read the
    live value first — that is the only place a user's saved setting lives — and
    only then fall back to the registered default and the caller's default.
    """
    try:
        value = getattr(opts, name, _MISSING)
    except Exception:
        value = _MISSING

    if value is not _MISSING:
        return value

    data = getattr(opts, "data", None)
    if isinstance(data, Mapping) and name in data:
        return data[name]

    labels = getattr(opts, "data_labels", None)
    if isinstance(labels, Mapping) and name in labels:
        return getattr(labels[name], "default", default)

    return default


def first_option(opts, names, default=None):
    """Return the first option out of ``names`` that this WebUI actually defines."""
    for name in names:
        value = option(opts, name, _MISSING)
        if value is not _MISSING:
            return value
    return default


def toprow_is_compact(opts):
    """Whether Toprow should render in its compact (inline) layout.

    Forge Neo replaced A1111's ``compact_prompt_box`` checkbox with the
    ``prompt_box_style`` radio.  When the compact layout is selected, Toprow
    defers rendering of the generate box until ``create_inline_toprow_image()``
    is called from the output panel, so this answer decides UI wiring, not just
    styling.
    """
    style = option(opts, "prompt_box_style", _MISSING)
    if style is not _MISSING:
        return style == "Compact"
    return bool(option(opts, "compact_prompt_box", False))


def media_source_kwargs(component_class, source="upload"):
    """Use the media source keyword supported by the installed Gradio version."""
    parameters = inspect.signature(component_class.__init__).parameters
    if "sources" in parameters:
        return {"sources": [source]}
    if "source" in parameters:
        return {"source": source}
    return {}


def supported_kwargs(callable_or_class, **kwargs):
    """Drop keyword arguments this WebUI's version of ``callable_or_class`` lacks.

    Used for processing fields that only exist on some forks (Forge Neo's
    ``distilled_cfg_scale``, for example) so mov2mov can pass them when they are
    available without crashing where they are not.
    """
    target = callable_or_class
    if inspect.isclass(target):
        target = target.__init__

    try:
        parameters = inspect.signature(target).parameters
    except (TypeError, ValueError):
        return dict(kwargs)

    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return dict(kwargs)

    return {k: v for k, v in kwargs.items() if k in parameters}
