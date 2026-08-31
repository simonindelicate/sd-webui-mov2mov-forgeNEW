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
    gallery: gr.Gallery = None
    video: gr.Video = None
    generation_info: gr.components.Component = None
    infotext: gr.HTML = None
    html_log: gr.HTML = None


def create_output_panel(tabname, outdir, toprow=None):
    """Build mov2mov's result panel.

    Unlike img2img, mov2mov produces a single video, never a gallery of images.
    The gallery here exists only as the surface Forge's ``requestProgress()``
    draws live previews onto; it never holds a value and is deliberately not
    wired into any event.  Feeding an always-empty ``gr.Gallery`` into an event's
    ``inputs`` is what produced Gradio 4's ``GalleryData`` validation errors, and
    there is nothing mov2mov could do with the value anyway.
    """
    res = OutputPanel()

    with gr.Column(elem_id=f"{tabname}_results"):
        if toprow is not None:
            # In the compact prompt layout Toprow defers rendering of the
            # generate box until here; without this call there is no Generate
            # button at all.
            toprow.create_inline_toprow_image()

        with gr.Column(variant="panel", elem_id=f"{tabname}_results_panel"):
            with gr.Group(elem_id=f"{tabname}_gallery_container"):
                gallery_height = option(shared.opts, "gallery_height", "") or None
                res.gallery = gr.Gallery(
                    label="Preview",
                    show_label=False,
                    elem_id=f"{tabname}_gallery",
                    columns=4,
                    preview=True,
                    height=gallery_height,
                    interactive=False,
                    show_download_button=False,
                )
                res.video = gr.Video(
                    label="Output",
                    show_label=False,
                    elem_id=f"{tabname}_video",
                    height=gallery_height,
                    interactive=False,
                )

            hide_dir_config = bool(option(shared.cmd_opts, "hide_ui_dir_config", False))
            save_dir = option(shared.opts, "outdir_save", "outputs/save")

            with gr.Row(elem_id=f"image_buttons_{tabname}", elem_classes="image-buttons"):
                open_folder_button = ToolButton(
                    folder_symbol,
                    elem_id=f"{tabname}_open_folder",
                    visible=not hide_dir_config,
                    tooltip="Open the mov2mov output directory.",
                )
                save = ToolButton(
                    "\U0001f4be",
                    elem_id=f"save_{tabname}",
                    tooltip=f"Save the video to a dedicated directory ({save_dir}).",
                )
                save_zip = ToolButton(
                    "\U0001f5c3️",
                    elem_id=f"save_zip_{tabname}",
                    tooltip=f"Save another copy of the video ({save_dir}).",
                )

            def open_output_folder():
                if hide_dir_config:
                    return
                util.open_folder(option(shared.opts, "outdir_samples", "") or outdir)

            # No inputs: the video output directory is a setting, not a gallery
            # selection, so this button needs no component values at all.
            open_folder_button.click(fn=open_output_folder, inputs=[], outputs=[])

            download_files = gr.File(
                None,
                file_count="multiple",
                interactive=False,
                show_label=False,
                visible=False,
                elem_id=f"download_files_{tabname}",
            )

            with gr.Group():
                res.infotext = gr.HTML(elem_id=f"html_info_{tabname}", elem_classes="infotext")
                res.html_log = gr.HTML(elem_id=f"html_log_{tabname}", elem_classes="html-log")
                res.generation_info = gr.Textbox(visible=False, elem_id=f"generation_info_{tabname}")

                save_args = dict(
                    fn=call_queue.wrap_gradio_call_no_job(save_video),
                    inputs=[res.video],
                    outputs=[download_files, res.html_log],
                )
                save.click(show_progress=False, **save_args)
                save_zip.click(**save_args)

    return res


def save_video(video):
    if not video:
        raise gr.Error("There is no mov2mov video to save yet.")

    # gr.Video hands back a filesystem path; older Gradio releases handed back a
    # (video, subtitles) pair.
    if isinstance(video, (tuple, list)):
        video = video[0]
    if isinstance(video, dict):
        video = video.get("name") or video.get("path") or video.get("video")

    path = "logs/movies"
    os.makedirs(path, exist_ok=True)

    index = len([name for name in os.listdir(path) if name.endswith(".mp4")]) + 1
    video_path = os.path.join(path, str(index).zfill(5) + ".mp4")
    shutil.copyfile(video, video_path)
    filename = os.path.relpath(video_path, path)

    return update(value=[video_path], visible=True), plaintext_to_html(f"Saved: {filename}")
