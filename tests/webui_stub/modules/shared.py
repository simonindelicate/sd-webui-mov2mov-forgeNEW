"""Minimal stand-in for Forge's modules.shared."""

import argparse
import sys


class OptionInfo:
    def __init__(self, default=None, label="", component=None, component_args=None, section=None, **kwargs):
        self.default = default
        self.label = label
        self.component = component
        self.component_args = component_args
        self.section = section
        self.do_not_save = False


class Options:
    """Mirrors Forge Neo's Options: unknown names raise AttributeError."""

    def __init__(self, data_labels):
        object.__setattr__(self, "data_labels", dict(data_labels))
        object.__setattr__(self, "data", {k: v.default for k, v in data_labels.items()})

    def __getattr__(self, item):
        data = object.__getattribute__(self, "data")
        if item in data:
            return data[item]
        labels = object.__getattribute__(self, "data_labels")
        if item in labels:
            return labels[item].default
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if key in ("data", "data_labels"):
            object.__setattr__(self, key, value)
        else:
            self.data[key] = value

    def add_option(self, key, info):
        self.data_labels[key] = info
        if key not in self.data:
            self.data[key] = info.default


# Deliberately close to a stock Forge Neo install: the A1111 options mov2mov used
# to read (compact_prompt_box, ...) are absent.
opts = Options(
    {
        "ui_reorder_list": OptionInfo([]),
        "prompt_box_style": OptionInfo("Default"),
        "gallery_height": OptionInfo(""),
        "outdir_save": OptionInfo("outputs/save"),
        "outdir_samples": OptionInfo(""),
        "open_dir_button_choice": OptionInfo("Subdirectory"),
        "enable_console_prompts": OptionInfo(False),
        "samples_log_stdout": OptionInfo(False),
        "do_not_show_images": OptionInfo(False),
        "initial_noise_multiplier": OptionInfo(1.0),
        "img2img_settings_accordion": OptionInfo(False),
        "dimensions_and_batch_together": OptionInfo(True),
        "res_step": OptionInfo(8),
        "interrupt_after_current": OptionInfo(True),
        "paste_safe_guard": OptionInfo(False),
        "include_styles_into_token_counters": OptionInfo(True),
    }
)

cmd_opts = argparse.Namespace(hide_ui_dir_config=False, freeze_settings=False)

hide_dirs = {}

progress_print_out = sys.stdout
sd_model = None
interrogator = None


class State:
    skipped = False
    interrupted = False
    stopping_generation = False
    job = ""
    job_count = 0

    def nextjob(self):
        pass

    def skip(self):
        pass

    def interrupt(self):
        pass

    def stop_generating(self):
        pass

    def begin(self, job=None):
        pass

    def end(self):
        pass


state = State()


class TotalTQDM:
    def clear(self):
        pass


total_tqdm = TotalTQDM()
