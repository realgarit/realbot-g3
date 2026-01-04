# Copyright (c) 2026 realgarit
import contextlib
import tkinter
from enum import Enum
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageDraw, ImageTk, ImageOps

from modules.map.map import (
    get_map_data_for_current_position,
    get_map_all_tiles,
)


class FancyTreeview:
    def __init__(
        self,
        root: ttk.Widget,
        height=22,
        row=0,
        column=0,
        column_span=1,
        additional_context_actions: Optional[dict[str, callable]] = None,
        on_highlight: Optional[callable] = None,
        on_double_click: Optional[callable] = None,
    ):
        if additional_context_actions is None:
            additional_context_actions = {}

        treeview_scrollbar_combo = ttk.Frame(root)
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.rowconfigure(0, weight=1)
        treeview_scrollbar_combo.grid(row=row, column=column, columnspan=column_span, sticky="NSWE")

        self._items = {}
        self._tv = ttk.Treeview(
            treeview_scrollbar_combo, columns="value", show="tree headings", selectmode="browse", height=height
        )

        self._tv.column("#0", width=220)
        self._tv.heading("#0", text="Key", anchor="w")
        self._tv.column("value", width=270)
        self._tv.heading("value", text="Value", anchor="w")

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky="NSWE")
        self._tv.configure(yscrollcommand=scrollbar.set)
        self._tv.grid(row=0, column=0, sticky="NSWE")

        self._context_menu = tkinter.Menu(self._tv, tearoff=0)
        self._context_menu.add_command(label="Copy Value", command=self._handle_copy)
        for action in additional_context_actions:
            self._context_menu.add_command(
                label=action, command=lambda a=action: self._handle_action(additional_context_actions[a])
            )

        self._tv.bind("<Button-3>", self._handle_right_click)
        self._tv.bind("<Up>", lambda _: root.focus_set())
        self._tv.bind("<Down>", lambda _: root.focus_set())
        self._tv.bind("<Left>", lambda _: root.focus_set())
        self._tv.bind("<Right>", lambda _: root.focus_set())

        if on_highlight is not None:
            self._tv.bind("<ButtonRelease-1>", lambda _: on_highlight(self._tv.item(self._tv.focus())["text"]))

        if on_double_click is not None:
            self._tv.bind("<Double-Button-1>", lambda _: on_double_click(self._tv.item(self._tv.focus())["text"]))

    def update_data(self, data: dict) -> None:
        found_items = self._update_dict(data, "", "")
        missing_items = set(self._items.keys()) - set(found_items)
        for key in missing_items:
            with contextlib.suppress(tkinter.TclError):
                self._tv.delete(self._items[key])
            del self._items[key]

    def _update_dict(self, data: any, key_prefix: str, parent: str) -> list[str]:
        found_items = []

        for key in data:
            item_key = f"{key_prefix}{key}"
            # BattleStateSide._battle_state is a circular reference.
            if key == "__value" or key == "_battle_state":
                pass
            elif type(data[key]) is dict:
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key].get("__value", ""),))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key].get("__value", ""),))
                    self._items[item_key] = item
                found_items.append(item_key)
                found_items.extend(self._update_dict(data[key], f"{key_prefix}{key}.", item))
            elif isinstance(data[key], (list, set, tuple, frozenset)):
                value = ""
                if isinstance(data[key], tuple):
                    value = str(data[key])

                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(value,))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(value,))
                    self._items[item_key] = item
                found_items.append(item_key)

                d = {str(i): data[key][i] for i in range(len(data[key]))}
                found_items.extend(self._update_dict(d, f"{key_prefix}{key}.", item))
            elif isinstance(data[key], (bool, int, float, complex, str, bytes, bytearray)):
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key],))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key],))
                    self._items[item_key] = item
                found_items.append(item_key)
            elif isinstance(data[key], Enum):
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key].name,))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key].name,))
                    self._items[item_key] = item
                found_items.append(item_key)
            else:
                if data[key].__str__ is not object.__str__:
                    value = str(data[key])
                else:
                    value = f"object({data[key].__class__.__name__})"

                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(value,))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(value,))
                    self._items[item_key] = item
                found_items.append(item_key)

                if hasattr(data[key], "debug_dict_value") and callable(data[key].debug_dict_value):
                    properties = data[key].debug_dict_value()
                else:
                    properties = {}
                    with contextlib.suppress(AttributeError):
                        for k in data[key].__dict__:
                            properties[k] = data[key].__dict__[k]
                    for k in dir(data[key].__class__):
                        if isinstance(getattr(data[key].__class__, k), property):
                            properties[k] = getattr(data[key], k)

                found_items.extend(self._update_dict(properties, f"{key_prefix}{key}.", item))

        return found_items

    def _handle_right_click(self, event) -> None:
        if item := self._tv.identify_row(event.y):
            self._tv.selection_set(item)
            self._context_menu.tk_popup(event.x_root, event.y_root)

    def _handle_copy(self) -> None:
        selection = self._tv.selection()
        if len(selection) < 1:
            return

        import pyperclip3

        pyperclip3.copy(str(self._tv.item(selection[0])["values"][0]))

    def _handle_action(self, callback: callable) -> None:
        selection = self._tv.selection()
        if len(selection) < 1:
            return

        callback(self._tv.item(selection[0])["text"])


class MapViewer:
    COLLISION = (255, 0, 0)
    ENCOUNTERS = (0, 255, 0)
    NORMAL = (255, 255, 255)
    JUMP = (0, 255, 255)
    WATER = (0, 0, 255)
    TILE_SIZE = 8

    def __init__(self, root: ttk.Widget, row=0, column=0) -> None:
        self._root = root
        self._map: ttk.Label = ttk.Label(self._root, padding=(10, 10))
        self._map.grid(row=row, column=column)
        self._cache: dict[tuple[int, int], ImageTk.PhotoImage] = {}

    def update(self):
        # If trainer data do not exists yet then ignore. eg. New game, intro, etc
        with contextlib.suppress(TypeError, RuntimeError):
            current_map_data = get_map_data_for_current_position()

            cached_map = self._cache.get((current_map_data.map_group, current_map_data.map_number), False)
            if not cached_map:
                cached_map = ImageTk.PhotoImage(self._get_map_bitmap())
                self._cache[(current_map_data.map_group, current_map_data.map_number)] = cached_map

            self._map.configure(image=cached_map)
            self._map.image = cached_map

    def _get_map_bitmap(self) -> Image:
        tiles = get_map_all_tiles()
        map_width, map_height = tiles[0].map_size

        image = Image.new(
            "RGB", (map_width * MapViewer.TILE_SIZE, map_height * MapViewer.TILE_SIZE), color=MapViewer.NORMAL
        )
        image_draw = ImageDraw.Draw(image)
        for y in range(map_height):
            for x in range(map_width):
                tile_data = tiles[x + map_width * y]
                tile_color = MapViewer.NORMAL
                if bool(tile_data.collision):
                    tile_color = MapViewer.COLLISION
                if tile_data.has_encounters:
                    tile_color = MapViewer.ENCOUNTERS
                if "Jump" in tile_data.tile_type:
                    tile_color = MapViewer.JUMP
                if tile_data.is_surfable:
                    tile_color = MapViewer.WATER
                image_draw.rectangle(
                    xy=(
                        (x * MapViewer.TILE_SIZE, y * MapViewer.TILE_SIZE),
                        ((x + 1) * MapViewer.TILE_SIZE, (y + 1) * MapViewer.TILE_SIZE),
                    ),
                    fill=tile_color,
                )

        return ImageOps.contain(image, (150, 150))
