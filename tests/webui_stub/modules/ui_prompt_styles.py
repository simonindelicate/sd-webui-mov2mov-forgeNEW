import gradio as gr

styles_materialize_symbol = "\U0001f4cb"


class UiPromptStyles:
    def __init__(self, tabname, main_ui_prompt, main_ui_negative_prompt):
        self.dropdown = gr.Dropdown(
            label="Styles",
            choices=[],
            value=[],
            multiselect=True,
            elem_id=f"{tabname}_styles",
        )

    def setup_apply_button(self, button):
        pass
