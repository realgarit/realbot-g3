# Copyright (c) 2026 realgarit
import time
import tkinter
from tkinter import ttk
from typing import TYPE_CHECKING, Union

from modules.context import context
from modules.game import _reverse_symbols, _symbols, decode_string
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.memory import get_symbol

if TYPE_CHECKING:
    from modules.libmgba import LibmgbaEmulator


class SymbolsTab(DebugTab):
    def __init__(self):
        self._tv = None
        self.symbols_to_display = {
            "gObjectEvents",
            "sChat",
            "gStringVar1",
            "gStringVar2",
            "gStringVar3",
            "gStringVar4",
            "gDisplayedStringBattle",
            "gBattleTypeFlags",
        }
        self.display_mode = {
            "gObjectEvents": None,
            "sChat": "str",
            "gStringVar1": "str",
            "gStringVar2": "str",
            "gStringVar3": "str",
            "gStringVar4": "str",
            "gDisplayedStringBattle": "str",
            "gBattleTypeFlags": "bin",
        }
        self._tv: FancyTreeview
        self._mini_window: Union[tkinter.Toplevel, None] = None

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=0, minsize=5)
        frame.rowconfigure(2, weight=1)

        button = ttk.Button(frame, text="Add Symbol to Watch", padding=0, command=self._add_new_symbol)
        button.grid(row=0, column=0, sticky="NE")

        context_actions = {
            "Remove from List": self._handle_remove_symbol,
            "Show as Hexadecimal Value": self._handle_show_as_hex,
            "Show as String": self._handle_show_as_string,
            "Show as Decimal Value": self._handle_show_as_dec,
            "Show as Binary Value": self._handle_show_as_bin,
        }

        self._tv = FancyTreeview(frame, row=2, height=20, additional_context_actions=context_actions)

        root.add(frame, text="Symbols")

    def _add_new_symbol(self):
        if self._mini_window is not None:
            return

        self._mini_window = tkinter.Toplevel(context.gui.window)
        self._mini_window.title("Add a symbol to list")
        self._mini_window.geometry("480x480")

        def remove_window(event=None):
            self._mini_window.destroy()
            self._mini_window = None

        self._mini_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._mini_window.rowconfigure(1, weight=1)
        self._mini_window.columnconfigure(0, weight=1)

        search_input = ttk.Entry(self._mini_window)
        search_input.grid(row=0, column=0, sticky="NWE")
        search_input.focus_force()

        tv_frame = ttk.Frame(self._mini_window)
        tv_frame.columnconfigure(0, weight=1)
        tv_frame.grid(row=1, column=0, sticky="NWSE")

        tv = ttk.Treeview(
            tv_frame, columns=("name", "address", "length"), show="headings", selectmode="browse", height=22
        )

        tv.column("name", width=300)
        tv.heading("name", text="Symbol Name")

        tv.column("address", width=90)
        tv.heading("address", text="Address")

        tv.column("length", width=90)
        tv.heading("length", text="Length")

        items: dict[str, str] = {}
        detached_items = set()
        for symbol, values in _symbols.items():
            address, length = values
            _, symbol, _ = _reverse_symbols[address]
            if length == 0:
                continue
            if not (symbol.startswith("s") or symbol.startswith("l") or symbol.startswith("g")):
                continue
            if symbol[1] != symbol[1].upper():
                continue
            if symbol in self.symbols_to_display:
                continue

            if symbol not in items:
                items[symbol] = tv.insert("", tkinter.END, text=symbol, values=(symbol, hex(address), hex(length)))

        def handle_input(event=None):
            search_term = search_input.get().strip().lower()
            for key in items:
                if search_term in key.lower() and key in detached_items:
                    tv.reattach(items[key], "", 0)
                    detached_items.remove(key)
                elif search_term not in key.lower() and key not in detached_items:
                    tv.detach(items[key])
                    detached_items.add(key)

        def sort_treeview(tv, col, reverse):
            try:
                data = [(int(tv.set(child, col), 16), child) for child in tv.get_children("")]
            except Exception:
                data = [(tv.set(child, col), child) for child in tv.get_children("")]
            data.sort(reverse=reverse)

            for index, item in enumerate(data):
                tv.move(item[1], "", index)

            tv.heading(col, command=lambda: sort_treeview(tv, col, not reverse))

        search_input.bind("<KeyRelease>", handle_input)

        def handle_double_click(event):
            if self._mini_window is None:
                return
            item = tv.identify_row(event.y)
            col = tv.identify_column(event.x)
            if item:
                symbol_name = tv.item(item)["text"]
                symbol_length = int(tv.item(item).get("values")[2], 16)
                if tv.item(item)["text"].startswith("s"):
                    self.display_mode[symbol_name] = "str"
                elif symbol_length in {2, 4}:
                    self.display_mode[symbol_name] = "dec"
                else:
                    self.display_mode[symbol_name] = "hex"
                self.symbols_to_display.add(tv.item(item)["text"])
                self.update(context.emulator)
            elif col:
                sort_treeview(tv, col, False)

        tv.bind("<Double-Button-1>", handle_double_click)

        scrollbar = ttk.Scrollbar(tv_frame, orient=tkinter.VERTICAL, command=tv.yview)
        scrollbar.grid(row=0, column=1, sticky="NWS")
        tv.configure(yscrollcommand=scrollbar.set)
        tv.grid(row=0, column=0, sticky="E")

        def handle_focus_out(event=None):
            if self._mini_window.focus_get() is None:
                remove_window()

        self._mini_window.bind("<FocusOut>", handle_focus_out)
        self._mini_window.bind("<Escape>", remove_window)
        self._mini_window.bind("<Control-q>", remove_window)

        while self._mini_window is not None and self._mini_window.state() != "destroyed":
            self._mini_window.update_idletasks()
            self._mini_window.update()
            time.sleep(1 / 60)

    def update(self, emulator: "LibmgbaEmulator"):
        data = {}

        for symbol in self.symbols_to_display:
            try:
                address, length = get_symbol(symbol.upper())
            except RuntimeError:
                self.symbols_to_display.remove(symbol)
                del self.display_mode[symbol]
                break

            value = emulator.read_bytes(address, length)
            display_mode = self.display_mode.get(symbol, "hex")

            if display_mode == "str":
                data[symbol] = decode_string(value)
            elif display_mode == "dec":
                n = int.from_bytes(value, byteorder="little")
                data[symbol] = f"{value.hex(' ', 1)} ({n})"
            elif display_mode == "bin":
                n = int.from_bytes(value, byteorder="little")
                binary_string = bin(n).removeprefix("0b").rjust(length * 8, "0")
                chunk_size = 4
                chunks = [binary_string[i : i + chunk_size] for i in range(0, len(binary_string), chunk_size)]
                data[symbol] = " ".join(chunks)
            else:
                data[symbol] = value.hex(" ", 1)

        self._tv.update_data(data)

    def _handle_remove_symbol(self, symbol: str):
        self.symbols_to_display.remove(symbol)
        del self.display_mode[symbol]

    def _handle_show_as_hex(self, symbol: str):
        self.display_mode[symbol] = "hex"

    def _handle_show_as_string(self, symbol: str):
        self.display_mode[symbol] = "str"

    def _handle_show_as_dec(self, symbol: str):
        self.display_mode[symbol] = "dec"

    def _handle_show_as_bin(self, symbol: str):
        self.display_mode[symbol] = "bin"
