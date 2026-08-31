"""Minimal stand-in for Forge's modules.script_callbacks."""

ui_settings_callbacks = []
ui_tabs_callbacks = []


def on_ui_settings(callback):
    ui_settings_callbacks.append(callback)


def on_ui_tabs(callback):
    ui_tabs_callbacks.append(callback)


def before_component_callback(component, **kwargs):
    pass


def after_component_callback(component, **kwargs):
    pass
