# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.context import context
from modules.game import _event_flags
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.memory import get_event_flag, set_event_flag

if TYPE_CHECKING:
    from modules.libmgba import LibmgbaEmulator


class EventFlagsTab(DebugTab):
    _tv: FancyTreeview
    _search_field: ttk.Entry

    def __init__(self):
        self._search_phrase = None

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        context_actions = {"Copy Name": self._copy_name, "Toggle Flag": self._toggle_flag}

        self._search_phrase = ""
        self._search_field = ttk.Entry(frame)
        self._search_field.grid(row=0, column=0, sticky="NWE")
        self._search_field.bind("<FocusIn>", self._handle_focus_in)
        self._search_field.bind("<FocusOut>", self._handle_focus_out)
        self._search_field.bind("<Control-a>", self._handle_ctrl_a)
        self._tv = FancyTreeview(frame, additional_context_actions=context_actions, height=21, row=1)
        root.add(frame, text="Flags")

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

    def _toggle_flag(self, flag: str):
        set_event_flag(flag)

    def _copy_name(self, flag: str):
        import pyperclip3

        pyperclip3.copy(flag)

    def _get_data(self):
        search_phrase = self._search_field.get().upper()

        return {flag: get_event_flag(flag) for flag in _event_flags if len(search_phrase) == 0 or search_phrase in flag}
