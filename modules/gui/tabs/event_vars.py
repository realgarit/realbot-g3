# Copyright (c) 2026 realgarit
import time
import tkinter
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.core.context import context
from modules.game.game import get_event_var_name
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.game.memory import get_event_var, set_event_var

if TYPE_CHECKING:
    from modules.game.libmgba import LibmgbaEmulator


class EventVarsTab(DebugTab):
    _tv: FancyTreeview
    _search_field: ttk.Entry

    def __init__(self):
        self._search_phrase = None
        self._mini_window: tkinter.Toplevel | None = None

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        context_actions = {"Copy Name": self._copy_name, "Change Value": self._change_value}

        self._search_phrase = ""
        self._search_field = ttk.Entry(frame)
        self._search_field.grid(row=0, column=0, sticky="NWE")
        self._search_field.bind("<FocusIn>", self._handle_focus_in)
        self._search_field.bind("<FocusOut>", self._handle_focus_out)
        self._search_field.bind("<Control-a>", self._handle_ctrl_a)
        self._tv = FancyTreeview(
            frame, additional_context_actions=context_actions, height=21, row=1, on_double_click=self._change_value
        )
        root.add(frame, text="Vars")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data())

    def _handle_focus_in(self, _):
        context.gui.inputs_enabled = False

    def _handle_focus_out(self, _):
        context.gui.inputs_enabled = True

    def _handle_ctrl_a(self, _):
        def select_all():
            self._search_field.select_range(0, "end")
            self._search_field.icursor("end")

        context.gui.window.after(50, select_all)

    def _copy_name(self, var: str):
        import pyperclip3

        pyperclip3.copy(var)

    def _change_value(self, var: str):
        if self._mini_window is not None:
            return

        self._mini_window = tkinter.Toplevel(context.gui.window)
        self._mini_window.title(f"Change variable {var}")
        self._mini_window.geometry("300x120")

        def remove_window(event=None):
            self._mini_window.destroy()
            self._mini_window = None

        self._mini_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._mini_window.rowconfigure(1, weight=1)
        self._mini_window.columnconfigure(0, weight=1)

        label = ttk.Label(self._mini_window, text=f"New value for {var}:")
        label.grid(row=0, column=0, sticky="NW", padx=10, pady=10)

        value_input = ttk.Entry(self._mini_window)
        value_input.grid(row=1, column=0, sticky="NWE", padx=10)
        value_input.insert(0, str(get_event_var(var)))
        value_input.focus_force()

        def select_all(widget: ttk.Entry):
            widget.select_range(0, "end")
            widget.icursor("end")

        self._mini_window.after(50, lambda: select_all(value_input))

        def handle_enter(*args):
            try:
                value = int(value_input.get())
                set_event_var(var, value)
                remove_window()
            except ValueError:
                pass

        button = ttk.Button(self._mini_window, text="Save", command=handle_enter)
        button.grid(row=2, column=0, sticky="SE", padx=10, pady=10)

        self._mini_window.bind("<Return>", handle_enter)
        self._mini_window.bind("<Escape>", remove_window)

        while self._mini_window is not None and self._mini_window.state() != "destroyed":
            self._mini_window.update_idletasks()
            self._mini_window.update()
            time.sleep(1 / 60)

    def _get_data(self):
        search_phrase = self._search_field.get().upper()

        data = {}
        for var in range(0x4000, 0x40FF):
            name = get_event_var_name(var)
            if len(search_phrase) == 0 or search_phrase in name:
                data[name] = get_event_var(name)

        return data
