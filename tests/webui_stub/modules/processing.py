"""Minimal stand-in for Forge's modules.processing."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(repr=False)
class StableDiffusionProcessing:
    sd_model: Any = None
    outpath_samples: str = None
    outpath_grids: str = None
    prompt: str = ""
    negative_prompt: str = ""
    styles: list = None
    seed: int = -1
    batch_size: int = 1
    n_iter: int = 1
    steps: int = 20
    cfg_scale: float = 7.0
    distilled_cfg_scale: float = 3.5
    width: int = 512
    height: int = 512
    do_not_save_grid: bool = False
    override_settings: dict = None
    subseed: int = -1
    subseed_strength: float = 0
    sampler_name: str = None
    comments: dict = field(default_factory=dict)
    user: str = field(default=None, init=False)
    scripts: Any = field(default=None, init=False)
    script_args: Any = field(default=None, init=False)
    init_images: list = None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@dataclass(repr=False)
class StableDiffusionProcessingImg2Img(StableDiffusionProcessing):
    resize_mode: int = 0
    denoising_strength: float = 0.75
    image_cfg_scale: float = None
    mask: Any = None
    mask_blur: int = 4
    inpainting_fill: int = 0
    inpaint_full_res: bool = True
    inpaint_full_res_padding: int = 0
    inpainting_mask_invert: int = 0
    initial_noise_multiplier: float = None


class Processed:
    def __init__(self, p, images_list, seed=-1, info="", **kwargs):
        self.images = images_list
        self.seed = seed
        self.info = info
        self.comments = ""

    def js(self):
        return "{}"


def fix_seed(p):
    pass


def process_images(p):
    raise AssertionError("process_images must not run during UI tests")
