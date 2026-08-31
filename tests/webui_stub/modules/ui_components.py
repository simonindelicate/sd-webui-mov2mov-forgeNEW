"""Original stand-ins for the WebUI's form components.

Only the behaviour extensions depend on: the `tool` button styling, rows and
groups that sit inside Gradio forms, and an accordion that doubles as a boolean
input.
"""

from functools import wraps

import gradio as gr
from modules import gradio_extensions  # noqa: F401  (patches Gradio on import)


class FormComponent:
    webui_do_not_create_gradio_pyi_thank_you = True

    def get_expected_parent(self):
        return gr.components.Form


gr.Dropdown.get_expected_parent = FormComponent.get_expected_parent


class ToolButton(gr.Button, FormComponent):
    @wraps(gr.Button.__init__)
    def __init__(self, value="", *args, elem_classes=None, **kwargs):
        super().__init__(*args, elem_classes=["tool", *(elem_classes or [])], value=value, **kwargs)

    def get_block_name(self):
        return "button"


class ResizeHandleRow(gr.Row):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elem_classes.append("resize-handle-row")

    def get_block_name(self):
        return "row"


class FormRow(gr.Row, FormComponent):
    pass


class FormColumn(gr.Column, FormComponent):
    pass


class FormGroup(gr.Group, FormComponent):
    pass


class FormHTML(gr.HTML, FormComponent):
    pass


class InputAccordionImpl(gr.Checkbox):
    """A boolean input rendered as an accordion that opens when it is true."""

    webui_do_not_create_gradio_pyi_thank_you = True

    global_index = 0

    @wraps(gr.Checkbox.__init__)
    def __init__(self, value=None, setup=False, **kwargs):
        if not setup:
            super().__init__(value=value, **kwargs)
            return

        self.accordion_id = kwargs.get("elem_id")
        if self.accordion_id is None:
            self.accordion_id = f"input-accordion-{InputAccordionImpl.global_index}"
            InputAccordionImpl.global_index += 1

        super().__init__(
            value=value,
            **{**kwargs, "elem_id": f"{self.accordion_id}-checkbox", "visible": False},
        )

        self.change(
            fn=None,
            _js=f'function(checked){{ inputAccordionChecked("{self.accordion_id}", checked); }}',
            inputs=[self],
        )

        self.accordion = gr.Accordion(
            **{
                **kwargs,
                "elem_id": self.accordion_id,
                "label": kwargs.get("label", "Accordion"),
                "elem_classes": ["input-accordion"],
                "open": value,
            }
        )

    def extra(self):
        return gr.Column(
            elem_id=f"{self.accordion_id}-extra", elem_classes="input-accordion-extra", min_width=0
        )

    def __enter__(self):
        self.accordion.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.accordion.__exit__(exc_type, exc_value, traceback)

    def get_block_name(self):
        return "checkbox"


def InputAccordion(value=None, **kwargs):
    return InputAccordionImpl(value=value, setup=True, **kwargs)
