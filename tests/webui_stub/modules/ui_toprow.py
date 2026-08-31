"""Original stand-in for the WebUI's Toprow.

The behaviour that matters to an extension is the layout split: in the compact
prompt style the generate box is created unrendered and only appears when the
output panel calls ``create_inline_toprow_image()``, and the prompts, tools and
styles are created from ``create_inline_toprow_prompts()`` rather than from the
constructor. A tab that ignores either ends up without a Generate button.
"""

import gradio as gr

from modules import images, shared, ui_prompt_styles
from modules.ui_components import ToolButton


class Toprow:
    prompt = None
    prompt_img = None
    negative_prompt = None

    interrupt = None
    interrupting = None
    skip = None
    submit = None

    paste = None
    clear_prompt_button = None
    apply_styles = None
    restore_progress_button = None

    token_counter = None
    token_button = None
    negative_token_counter = None
    negative_token_button = None

    ui_styles = None
    submit_box = None

    def __init__(self, is_img2img, *, is_compact=None, id_part=None):
        self.is_img2img = is_img2img
        self.id_part = id_part or ("img2img" if is_img2img else "txt2img")

        if is_compact is None:
            is_compact = shared.opts.prompt_box_style == "Compact"
        self.is_compact = is_compact

        if is_compact:
            self.create_submit_box()
        else:
            with gr.Row(elem_id=f"{self.id_part}_toprow", variant="compact"):
                self.create_classic_toprow()

    def create_classic_toprow(self):
        self.create_prompts()
        with gr.Column(scale=1, elem_id=f"{self.id_part}_actions_column"):
            self.create_submit_box()
            self.create_tools_row()
            self.create_styles_ui()

    def create_inline_toprow_prompts(self):
        if not self.is_compact:
            return

        self.create_prompts()
        with gr.Row(elem_classes=["toprow-compact-stylerow"]):
            with gr.Column(elem_classes=["toprow-compact-tools"]):
                self.create_tools_row()
            with gr.Column():
                self.create_styles_ui()

    def create_inline_toprow_image(self):
        if not self.is_compact:
            return
        self.submit_box.render()

    def create_prompts(self):
        with gr.Column(elem_id=f"{self.id_part}_prompt_container", scale=6):
            with gr.Row(elem_id=f"{self.id_part}_prompt_row", elem_classes=["prompt-row"]):
                self.prompt = gr.Textbox(
                    label="Prompt",
                    elem_id=f"{self.id_part}_prompt",
                    show_label=False,
                    lines=3,
                    elem_classes=["prompt"],
                )
                self.prompt_img = gr.File(
                    elem_id=f"{self.id_part}_prompt_image",
                    file_count="single",
                    type="binary",
                    visible=False,
                )

            with gr.Row(elem_id=f"{self.id_part}_neg_prompt_row", elem_classes=["prompt-row"]):
                self.negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    elem_id=f"{self.id_part}_neg_prompt",
                    show_label=False,
                    lines=3,
                    elem_classes=["prompt"],
                )

        # Registered from the constructor: this is why a tab callback needs its
        # own Blocks context.
        self.prompt_img.change(
            fn=images.image_data,
            inputs=[self.prompt_img],
            outputs=[self.prompt, self.prompt_img],
            show_progress=False,
        )

    def create_submit_box(self):
        with gr.Row(
            elem_id=f"{self.id_part}_generate_box",
            elem_classes=["generate-box"],
            render=not self.is_compact,
        ) as submit_box:
            self.submit_box = submit_box

            self.interrupt = gr.Button("Interrupt", elem_id=f"{self.id_part}_interrupt")
            self.skip = gr.Button("Skip", elem_id=f"{self.id_part}_skip")
            self.interrupting = gr.Button("Interrupting...", elem_id=f"{self.id_part}_interrupting")
            self.submit = gr.Button("Generate", elem_id=f"{self.id_part}_generate", variant="primary")

            self.skip.click(fn=shared.state.skip)
            self.interrupt.click(fn=shared.state.interrupt)
            self.interrupting.click(fn=shared.state.interrupt)

    def create_tools_row(self):
        with gr.Row(elem_id=f"{self.id_part}_tools"):
            from modules.ui import clear_prompt_symbol, paste_symbol, restore_progress_symbol

            self.paste = ToolButton(value=paste_symbol, elem_id="paste")
            self.clear_prompt_button = ToolButton(
                value=clear_prompt_symbol, elem_id=f"{self.id_part}_clear_prompt"
            )
            self.apply_styles = ToolButton(
                value=ui_prompt_styles.styles_materialize_symbol,
                elem_id=f"{self.id_part}_style_apply",
            )
            self.restore_progress_button = ToolButton(
                value=restore_progress_symbol,
                elem_id=f"{self.id_part}_restore_progress",
                visible=False,
            )

            self.token_counter = gr.HTML(
                value="<span>0/75</span>", elem_id=f"{self.id_part}_token_counter", visible=False
            )
            self.token_button = gr.Button(visible=False, elem_id=f"{self.id_part}_token_button")
            self.negative_token_counter = gr.HTML(
                value="<span>0/75</span>",
                elem_id=f"{self.id_part}_negative_token_counter",
                visible=False,
            )
            self.negative_token_button = gr.Button(
                visible=False, elem_id=f"{self.id_part}_negative_token_button"
            )

            self.clear_prompt_button.click(
                fn=lambda *x: x,
                _js="confirm_clear_prompt",
                inputs=[self.prompt, self.negative_prompt],
                outputs=[self.prompt, self.negative_prompt],
                show_progress=False,
            )

    def create_styles_ui(self):
        self.ui_styles = ui_prompt_styles.UiPromptStyles(
            self.id_part, self.prompt, self.negative_prompt
        )
        self.ui_styles.setup_apply_button(self.apply_styles)

    def hook_paste_guard(self):
        self.negative_prompt.change(
            fn=lambda prompt: gr.update(interactive=not bool(prompt.strip())),
            inputs=[self.negative_prompt],
            outputs=[self.paste],
            show_progress=False,
            queue=False,
        )
