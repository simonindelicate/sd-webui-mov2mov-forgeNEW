"""Minimal stand-in for the parts of Forge's modules.ui that mov2mov imports."""

import math

import gradio as gr

from modules import shared, shared_items
from modules.shared import opts

switch_values_symbol = "\U000021c5"
detect_image_size_symbol = "\U0001f4d0"
paste_symbol = "↙️"
clear_prompt_symbol = "\U0001f5d1️"
restore_progress_symbol = "\U0001f300"


def _round(value):
    step = int(opts.res_step)
    return math.floor(value / step + 0.5) * step


def resize_from_to_html(width, height, scale_by):
    target_width = _round(float(width) * scale_by)
    target_height = _round(float(height) * scale_by)

    if not target_width or not target_height:
        return "no image selected"

    return f"resize: from {width}x{height} to {target_width}x{target_height}"


def ordered_ui_categories():
    user_order = {x.strip(): i * 2 + 1 for i, x in enumerate(shared.opts.ui_reorder_list)}

    for _, category in sorted(
        enumerate(shared_items.ui_reorder_categories()),
        key=lambda x: user_order.get(x[1], x[0] * 2 + 0),
    ):
        yield category


def create_override_settings_dropdown(tabname, row):
    dropdown = gr.Dropdown(
        [], label="Override settings", visible=False, elem_id=f"{tabname}_override_settings", multiselect=True
    )
    dropdown.change(fn=lambda x: gr.update(visible=bool(x)), inputs=[dropdown], outputs=[dropdown])
    return dropdown
