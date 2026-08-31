import dataclasses
import os
import shutil
import gradio as gr

from modules import call_queue, shared, util
from modules.ui_common import plaintext_to_html
from modules.ui_components import ToolButton

from scripts.m2m_compat import option, update


folder_symbol = "\U0001f4c2"  # 📂
refresh_symbol = "\U0001f504"  # 🔄


@dataclasses.dataclass
class OutputPanel:
    gallery = None
    video = None
    generation_info = None
    infotext = None
    html_log = None
    button_upscale = None

def create_output_panel(tabname, outdir, toprow=None):
    res = OutputPanel()

    def open_folder(f):
        if option(shared.cmd_opts, "hide_ui_dir_config", False):
            return
        util.open_folder(f)

    with gr.Column(elem_id=f"{tabname}_results"):
        if toprow:
            toprow.create_inline_toprow_image()

        with gr.Column(variant='panel', elem_id=f"{tabname}_results_panel"):
            with gr.Group(elem_id=f"{tabname}_gallery_container"):
                gallery_height = option(shared.opts, "gallery_height") or None
                res.gallery = gr.Gallery(label='Output', show_label=False, elem_id=f"{tabname}_gallery", columns=4, preview=True, height=gallery_height)
                res.video = gr.Video(label='Output', show_label=False, elem_id=f"{tabname}_video", height=gallery_height)

            with gr.Row(elem_id=f"image_buttons_{tabname}", elem_classes="image-buttons"):
                open_folder_button = ToolButton(folder_symbol, elem_id=f'{tabname}_open_folder', visible=not option(shared.cmd_opts, "hide_ui_dir_config", False), tooltip="Open images output directory.")

                if tabname != "extras":
                    save_dir = option(shared.opts, "outdir_save", "outputs/save")
                    save = ToolButton('💾', elem_id=f'save_{tabname}', tooltip=f"Save the video to a dedicated directory ({save_dir}).")
                    save_zip = ToolButton('🗃️', elem_id=f'save_zip_{tabname}', tooltip=f"Save another copy of the video ({save_dir})")

            open_folder_button.click(
                fn=lambda: open_folder(outdir),
                inputs=[],
                outputs=[],
            )

            if tabname != "extras":
                download_files = gr.File(None, file_count="multiple", interactive=False, show_label=False, visible=False, elem_id=f'download_files_{tabname}')

                with gr.Group():
                    res.infotext = gr.HTML(elem_id=f'html_info_{tabname}', elem_classes="infotext")
                    res.html_log = gr.HTML(elem_id=f'html_log_{tabname}', elem_classes="html-log")

                    res.generation_info = gr.Textbox(visible=False, elem_id=f'generation_info_{tabname}')
                    save.click(
                        fn=call_queue.wrap_gradio_call_no_job(save_video),
                        _js="(video) => [video]",
                        inputs=[
                            res.video,
                        ],
                        outputs=[
                            download_files,
                            res.html_log,
                        ],
                        show_progress=False,
                    )

                    save_zip.click(
                        fn=call_queue.wrap_gradio_call_no_job(save_video),
                        _js="(video) => [video]",
                        inputs=[
                            res.video,
                        ],
                        outputs=[
                            download_files,
                            res.html_log,
                        ]
                    )

            else:
                res.generation_info = gr.HTML(elem_id=f'html_info_x_{tabname}')
                res.infotext = gr.HTML(elem_id=f'html_info_{tabname}', elem_classes="infotext")
                res.html_log = gr.HTML(elem_id=f'html_log_{tabname}')

    return res


def save_video(video):
    path = "logs/movies"
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    index = len([path for path in os.listdir(path) if path.endswith(".mp4")]) + 1
    video_path = os.path.join(path, str(index).zfill(5) + ".mp4")
    shutil.copyfile(video, video_path)
    filename = os.path.relpath(video_path, path)
    return update(value=video_path, visible=True), plaintext_to_html(
        f"Saved: {filename}"
    )
