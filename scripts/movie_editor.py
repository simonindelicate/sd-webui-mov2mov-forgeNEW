import platform

import gradio as gr
import pandas
from PIL import Image
from tqdm import tqdm

from modules import shared
from modules.ui_components import InputAccordion, ToolButton
from scripts import m2m_util
from scripts.m2m_compat import media_source_kwargs, update

try:
    from modules import deepbooru as deepbooru_module
except ImportError:
    deepbooru_module = None


class MovieEditor:
    def __init__(self, id_part, gr_movie: gr.Video, gr_fps: gr.Slider):
        self.gr_eb_weight = None
        self.gr_df = None
        self.gr_keyframe = None
        self.gr_frame_number = None
        self.gr_frame_image = None
        self.gr_movie = gr_movie
        self.gr_fps = gr_fps
        self.gr_enable_movie_editor = None

        self.is_windows = platform.system() == "Windows"
        self.id_part = id_part
        self.frames = []
        self.frame_count = 0
        self.selected_data_frame = -1

    def render(self):
        id_part = self.id_part
        with InputAccordion(
            True, label="Movie Editor", elem_id=f"{id_part}_editor_accordion"
        ):
            gr.HTML(
                "<div style='color:red;font-weight: bold;border: 2px solid yellow;padding: 10px;font-size: 20px;'>"
                "This feature is in beta version!!! <br>"
                "It only supports Windows!!! <br>"
                "Make sure you have installed the ControlNet and IP-Adapter models."
                "</div>"
            )

            self.gr_enable_movie_editor = gr.Checkbox(
                label="Enable Movie Editor",
                elem_id=f"{id_part}_editor_enable",
            )

            self.gr_frame_image = gr.Image(
                label="Frame",
                elem_id=f"{id_part}_video_frame",
                **media_source_kwargs(gr.Image),
                visible=False,
                height=480,
            )

            # key frame tabs
            with gr.Tabs(elem_id=f"{id_part}_keyframe_tabs"):
                with gr.TabItem("Custom", id=f"{id_part}_keyframe_tab_custom"):
                    with gr.Row():
                        self.gr_frame_number = gr.Slider(
                            label="Frame number",
                            elem_id=f"{id_part}_video_frame_number",
                            step=1,
                            maximum=0,
                            minimum=0,
                        )

                with gr.TabItem("Auto", elem_id=f"{id_part}_keyframe_tab_auto"):
                    with gr.Row():
                        key_frame_interval = gr.Slider(
                            label="Key frame interval",
                            elem_id=f"{id_part}_video_keyframe_interval",
                            step=1,
                            maximum=100,
                            minimum=0,
                            value=2,
                        )
                        key_frame_interval_generate = ToolButton(
                            "♺",
                            elem_id=f"{id_part}_video_editor_auto_keyframe",
                            visible=True,
                            tooltip="generate",
                        )

            with gr.Row(elem_id=f"{id_part}_keyframe_custom_container"):
                add_keyframe = ToolButton(
                    "✚",
                    elem_id=f"{id_part}_video_editor_add_keyframe",
                    visible=True,
                    tooltip="Add keyframe",
                )
                remove_keyframe = ToolButton(
                    "✖",
                    elem_id=f"{id_part}_video_editor_remove_keyframe",
                    visible=True,
                    tooltip="Remove selected keyframe",
                )

                clear_keyframe = ToolButton(
                    "🗑",
                    elem_id=f"{id_part}_video_editor_clear_keyframe",
                    visible=True,
                    tooltip="Clear keyframe",
                )

            with gr.Row():
                data_frame = gr.Dataframe(
                    headers=["id", "frame", "prompt"],
                    datatype=["number", "number", "str"],
                    row_count=1,
                    col_count=(3, "fixed"),
                    max_rows=None,
                    height=480,
                    elem_id=f"{id_part}_video_editor_custom_data_frame",
                )
                self.gr_df = data_frame

            with gr.Row():
                interrogate = gr.Button(
                    value="Clip Interrogate Keyframe",
                    size="sm",
                    elem_id=f"{id_part}_video_editor_interrogate",
                )
                deepbooru = gr.Button(
                    value="Deepbooru Keyframe",
                    size="sm",
                    elem_id=f"{id_part}_video_editor_deepbooru",
                    interactive=deepbooru_module is not None,
                    tooltip=(
                        "Tag keyframes with Deepbooru"
                        if deepbooru_module is not None
                        else "Unavailable: Forge Neo does not include Deepbooru"
                    ),
                )

            with gr.Row():
                self.gr_eb_weight = gr.Slider(
                    label="EbSynth weight",
                    elem_id=f"{id_part}_video_eb_weight",
                    step=0.1,
                    maximum=10,
                    minimum=0,
                    value=4.0,
                )

        self.gr_movie.change(
            fn=self.movie_change,
            inputs=[self.gr_movie],
            outputs=[self.gr_frame_image, self.gr_frame_number, self.gr_fps],
            show_progress=True,
        )

        self.gr_frame_number.change(
            fn=self.movie_frame_change,
            inputs=[self.gr_movie, self.gr_frame_number],
            outputs=[self.gr_frame_image],
            show_progress=True,
        )

        self.gr_fps.change(
            fn=self.fps_change,
            inputs=[self.gr_movie, self.gr_fps],
            outputs=[self.gr_frame_image, self.gr_frame_number],
            show_progress=True,
        )

        data_frame.select(self.data_frame_select, data_frame, self.gr_frame_number)

        add_keyframe.click(
            fn=self.add_keyframe_click,
            inputs=[data_frame, self.gr_frame_number],
            outputs=[data_frame],
            show_progress=False,
        )
        remove_keyframe.click(
            fn=self.remove_keyframe_click,
            inputs=[data_frame],
            outputs=[data_frame],
            show_progress=False,
        )

        clear_keyframe.click(
            fn=lambda df: df.drop(df.index, inplace=True),
            inputs=[data_frame],
            outputs=[data_frame],
            show_progress=False,
        )

        key_frame_interval_generate.click(
            fn=self.key_frame_interval_generate_click,
            inputs=[data_frame, key_frame_interval],
            outputs=[data_frame],
            show_progress=True,
        )

        interrogate.click(
            fn=self.interrogate_keyframe,
            inputs=[data_frame],
            outputs=[data_frame],
            show_progress=True,
        )

        deepbooru.click(
            fn=self.deepbooru_keyframe,
            inputs=[data_frame],
            outputs=[data_frame],
            show_progress=True,
        )

    def interrogate_keyframe(self, data_frame: pandas.DataFrame):
        """
        Interrogate key frame
        """
        bar = tqdm(total=len(data_frame))
        for index, row in data_frame.iterrows():
            if row["frame"] <= 0:
                continue
            bar.set_description(f'Interrogate key frame {row["frame"]}')
            frame = row["frame"] - 1
            image = self.frames[frame]
            image = Image.fromarray(image)
            prompt = shared.interrogator.interrogate(image.convert("RGB"))
            data_frame.at[index, "prompt"] = prompt
            bar.update(1)

        return data_frame

    def deepbooru_keyframe(self, data_frame: pandas.DataFrame):
        """
        Deepbooru key frame

        """
        if deepbooru_module is None:
            raise gr.Error(
                "Deepbooru keyframe tagging is unavailable because this Forge Neo "
                "installation does not provide modules.deepbooru. Other Movie Editor "
                "features remain available."
            )

        bar = tqdm(total=len(data_frame))
        for index, row in data_frame.iterrows():
            if row["frame"] <= 0:
                continue
            bar.set_description(f'Interrogate key frame {row["frame"]}')
            frame = row["frame"] - 1
            image = self.frames[frame]
            image = Image.fromarray(image)
            prompt = deepbooru_module.model.tag(image)
            data_frame.at[index, "prompt"] = prompt
            bar.update(1)

        return data_frame

    def data_frame_select(self, event: gr.SelectData, data_frame: pandas.DataFrame):
        row, col = event.index
        self.selected_data_frame = row
        row = data_frame.iloc[row]
        frame = row["frame"]
        if 0 < frame <= self.frame_count:
            return int(frame)
        else:
            return 0

    def add_keyframe_click(self, data_frame: pandas.DataFrame, gr_frame_number: int):
        """
        Add a key frame to the data frame
        """
        if gr_frame_number < 1:
            return data_frame

        data_frame = data_frame[data_frame["frame"] > 0]

        if gr_frame_number in data_frame["frame"].values:
            return data_frame

        row = {"id": len(data_frame), "frame": gr_frame_number, "prompt": ""}
        data_frame.loc[len(data_frame)] = row

        data_frame = data_frame.sort_values(by="frame").reset_index(drop=True)

        data_frame["id"] = range(len(data_frame))

        return data_frame

    def remove_keyframe_click(self, data_frame: pandas.DataFrame):
        """
        Remove the selected key frame
        """
        if self.selected_data_frame < 0:
            return data_frame

        data_frame = data_frame.drop(self.selected_data_frame)

        data_frame = data_frame.sort_values(by="frame").reset_index(drop=True)

        data_frame["id"] = range(len(data_frame))

        return data_frame

    def key_frame_interval_generate_click(
        self, data_frame: pandas.DataFrame, key_frame_interval: int
    ):
        if key_frame_interval < 1:
            return data_frame

        # 按照key_frame_interval的间隔添加关键帧
        for i in range(0, self.frame_count, key_frame_interval):
            data_frame = self.add_keyframe_click(data_frame, i + 1)

        # 添加最后一帧
        data_frame = self.add_keyframe_click(data_frame, self.frame_count)

        return data_frame

    def movie_change(self, movie_path):
        if not movie_path:
            return (
                update(visible=False),
                update(maximum=0, minimum=0),
                update(),
            )
        fps = m2m_util.get_mov_fps(movie_path)
        self.frames = m2m_util.get_mov_all_images(movie_path, fps, True)

        self.frame_count = len(self.frames)
        return (
            update(visible=True),
            update(maximum=self.frame_count, minimum=0, value=0),
            update(maximum=fps, minimum=0, value=fps),
        )

    def movie_frame_change(self, movie_path, frame_number):
        if not movie_path:
            return update(visible=False)

        if frame_number <= 0:
            return update(
                visible=True, label=f"Frame: {frame_number}", value=None
            )

        return update(
            visible=True,
            label=f"Frame: {frame_number}",
            value=self.frames[frame_number - 1],
        )

    def fps_change(self, movie_path, fps):
        if not movie_path:
            return update(visible=False), update(
                maximum=0, minimum=0
            )

        self.frames = m2m_util.get_mov_all_images(movie_path, fps, True)
        self.frame_count = len(self.frames)
        return (
            update(visible=True),
            update(maximum=self.frame_count, minimum=0, value=0),
        )
