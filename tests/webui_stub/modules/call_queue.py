"""Minimal stand-in for Forge's modules.call_queue."""

from functools import wraps


def wrap_queued_call(func):
    return func


def wrap_gradio_gpu_call(func, extra_outputs=None):
    return wrap_gradio_call(func, extra_outputs=extra_outputs, add_stats=True)


def wrap_gradio_call(func, extra_outputs=None, add_stats=False):
    return wrap_gradio_call_no_job(func, extra_outputs, add_stats)


def wrap_gradio_call_no_job(func, extra_outputs=None, add_stats=False):
    @wraps(func)
    def f(*args, extra_outputs_array=extra_outputs, **kwargs):
        try:
            res = list(func(*args, **kwargs))
        except Exception as e:
            if extra_outputs_array is None:
                extra_outputs_array = [None, ""]
            res = extra_outputs_array + [f"<div class='error'>{e}</div>"]
        return tuple(res)

    return f
