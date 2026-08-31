"""Cut-down copy of Forge Neo's ScriptRunner argument accounting.

The offsets are the point: ``prepare_ui()`` resets ``inputs`` and every control
created after it is addressed by the ``args_from``/``args_to`` slice recorded at
creation time. Getting that ordering wrong is invisible until a script reads
somebody else's arguments, so the stub keeps the real bookkeeping.
"""

import gradio as gr

scripts_current = None
script_callbacks = None  # populated below, mirrors Forge's module attribute


class Script:
    filename = "stub.py"
    name = None
    alwayson = False
    is_img2img = False
    section = None
    sorting_priority = 0
    create_group = True
    group = None
    controls = None
    args_from = None
    args_to = None
    infotext_fields = None
    paste_field_names = None

    def title(self):
        return self.__class__.__name__

    def ui(self, is_img2img):
        return []

    def run(self, p, *args):
        return None


#: Script classes the stub runner should instantiate. Tests append to this.
scripts_data = []


class ScriptRunner:
    def __init__(self):
        self.scripts = []
        self.selectable_scripts = []
        self.alwayson_scripts = []
        self.inputs = [None]
        self.infotext_fields = []
        self.paste_field_names = []

    def initialize_scripts(self, is_img2img):
        self.scripts.clear()
        self.alwayson_scripts.clear()
        self.selectable_scripts.clear()

        for script_class in scripts_data:
            script = script_class()
            script.is_img2img = is_img2img
            self.scripts.append(script)
            if script.alwayson:
                self.alwayson_scripts.append(script)
            else:
                self.selectable_scripts.append(script)

    def create_script_ui(self, script):
        script.args_from = len(self.inputs)
        script.args_to = len(self.inputs)

        controls = script.ui(script.is_img2img)
        script.controls = controls
        if controls is None:
            return

        self.inputs += controls
        script.args_to = len(self.inputs)

    def setup_ui_for_section(self, section, scriptlist=None):
        if scriptlist is None:
            scriptlist = self.alwayson_scripts

        for script in sorted(scriptlist, key=lambda x: x.sorting_priority):
            if script.alwayson and script.section != section:
                continue

            if script.create_group:
                with gr.Group(visible=script.alwayson) as group:
                    self.create_script_ui(script)
                script.group = group
            else:
                self.create_script_ui(script)

    def prepare_ui(self):
        self.inputs = [None]

    def setup_ui(self):
        self.titles = [script.title() for script in self.selectable_scripts]

        self.setup_ui_for_section(None)

        dropdown = gr.Dropdown(
            label="Script", elem_id="script_list", choices=["None"] + self.titles, value="None", type="index"
        )
        self.inputs[0] = dropdown

        self.setup_ui_for_section(None, self.selectable_scripts)

        return self.inputs

    def run(self, p, *args):
        script_index = args[0]
        if not script_index:
            return None
        script = self.selectable_scripts[script_index - 1]
        return script.run(p, *args[script.args_from : script.args_to])

    def before_process(self, p):
        pass

    def process(self, p):
        pass


import modules.script_callbacks as script_callbacks  # noqa: E402
