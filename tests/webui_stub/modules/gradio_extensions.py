"""Original re-implementation of the Gradio patches an extension relies on.

Forge patches Gradio so that WebUI code can keep using `_js=`, `tooltip=` and the
Gradio 3 `source=` keyword, and so that keyword arguments Gradio has since
removed are warned about and dropped rather than raising. Extensions are written
against that behaviour, so the stub reproduces it — from the observable
behaviour, not from Forge's source.
"""

import inspect
import warnings
from functools import wraps

import gradio as gr
import gradio.blocks
import gradio.component_meta
import gradio.events


class GradioDeprecationWarning(DeprecationWarning):
    pass


# Gradio writes .pyi files next to any subclassed component; Forge suppresses
# that, and the stub has no business dropping generated files into the repo.
gradio.component_meta.create_or_modify_pyi = lambda *args, **kwargs: None
gradio.component_meta.updateable = lambda fn: fn


def _wrap_event(bound_event):
    @wraps(bound_event)
    def event(*args, _js=None, **kwargs):
        if _js is not None:
            kwargs["js"] = _js
        return bound_event(*args, **kwargs)

    return event


def _repair(component_class):
    if not getattr(component_class, "EVENTS", None):
        return

    original_init = component_class.__init__

    @wraps(original_init)
    def __init__(self, *args, tooltip=None, source=None, **kwargs):
        if source is not None:
            kwargs["sources"] = [source]

        allowed = inspect.signature(original_init).parameters
        accepted = {}
        for key, value in kwargs.items():
            if key in allowed:
                accepted[key] = value
            else:
                warnings.warn(
                    f"unexpected argument for {component_class.__name__}: {key}",
                    GradioDeprecationWarning,
                    stacklevel=2,
                )

        original_init(self, *args, **accepted)

        self.webui_tooltip = tooltip
        self.elem_classes = [f"gradio-{self.get_block_name()}", *(self.elem_classes or [])]

        for name in self.EVENTS:
            setattr(self, str(name), _wrap_event(getattr(self, str(name))))

    component_class.__init__ = __init__
    component_class.update = gr.update


for _name in set(gr.components.__all__ + gr.layouts.__all__):
    _repair(getattr(gr, _name, None))


def _add_classes(block):
    block.elem_classes = [f"gradio-{block.get_block_name()}", *(block.elem_classes or [])]


_original_block_context_init = gradio.blocks.BlockContext.__init__


@wraps(_original_block_context_init)
def _block_context_init(self, *args, **kwargs):
    result = _original_block_context_init(self, *args, **kwargs)
    _add_classes(self)
    return result


# Layout components carry no events, so _repair() skips them; Forge still gives
# them their gradio-* class, and code such as ResizeHandleRow relies on
# elem_classes being a list by the time the constructor returns.
gradio.blocks.BlockContext.__init__ = _block_context_init


class Dependency(gradio.events.Dependency):
    """Accept ``_js`` on ``.then()`` as well as on the event itself."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.then = _wrap_event(self.then)


gradio.events.Dependency = Dependency
