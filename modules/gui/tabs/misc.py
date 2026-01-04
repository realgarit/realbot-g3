# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.clock import get_clock_time, get_play_time
from modules.context import context
from modules.daycare import get_daycare_data
from modules.fishing import get_feebas_tiles
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.memory import game_has_started, read_symbol
from modules.menuing import is_fade_active
from modules.region_map import get_map_cursor
from modules.roamer import get_roamer, get_roamer_location_history
from modules.text_printer import get_text_printer

if TYPE_CHECKING:
    from modules.libmgba import LibmgbaEmulator


class MiscTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Misc")

    def update(self, emulator: "LibmgbaEmulator"):
        try:
            data = self._get_data()
        except Exception as e:
            if game_has_started():
                raise
            else:
                data = {e.__class__.__name__: str(e)}

        self._tv.update_data(data)

    def _get_data(self):
        data = get_daycare_data()
        if data is None:
            daycare_information = {}
        else:
            if data.pokemon1 is not None and not data.pokemon1.is_empty:
                gender = ""
                if data.pokemon1.gender is not None:
                    gender = f" ({data.pokemon1.gender})"

                pokemon1 = {
                    "__value": f"{data.pokemon1.species.name}{gender}; {data.pokemon1_steps:,} steps",
                    "pokemon": data.pokemon1,
                    "steps": data.pokemon1_steps,
                    "egg_groups": ", ".join(set(data.pokemon1_egg_groups)),
                }
            else:
                pokemon1 = "n/a"

            if data.pokemon2 is not None and not data.pokemon2.is_empty:
                gender = "" if data.pokemon2.gender is None else f" ({data.pokemon2.gender})"
                pokemon2 = {
                    "__value": f"{data.pokemon2.species.name}{gender}; {data.pokemon1_steps:,} steps",
                    "pokemon": data.pokemon2,
                    "steps": data.pokemon2_steps,
                    "egg_groups": ", ".join(set(data.pokemon2_egg_groups)),
                }
            else:
                pokemon2 = "n/a"

            if pokemon1 == "n/a" and pokemon2 == "n/a":
                daycare_value = "None"
            elif pokemon2 == "n/a":
                daycare_value = pokemon1["__value"]
            elif pokemon1 == "n/a":
                daycare_value = pokemon2["__value"]
            else:
                daycare_value = (
                    f"{data.compatibility[0].name}: {data.pokemon1.species.name} and {data.pokemon2.species.name}"
                )

            daycare_information = {
                "__value": daycare_value,
                "Pokémon #1": pokemon1,
                "Pokémon #2": pokemon2,
                "Offspring Personality": data.offspring_personality,
                "Step Counter": data.step_counter,
                "Compatibility": data.compatibility[0].name,
                "Compatibility Reason": data.compatibility[1],
            }

        if game_has_started():
            location_history = {"__value": []}
            for index, location in enumerate(get_roamer_location_history()):
                if index == 0:
                    location_history["Current Map"] = location.pretty_name
                else:
                    # Do not show the current map in the short-form location history to save space.
                    location_history["__value"].append(location.pretty_name)
                    location_history[f"Current-{index} Map"] = location.pretty_name
            location_history["__value"] = ", ".join(location_history["__value"])
        else:
            location_history = None

        block_data = {
            "Daycare": daycare_information,
            "Roamer": get_roamer() if game_has_started() else None,
            "Location History": location_history,
            "Feebas Tiles": get_feebas_tiles() if game_has_started() else None,
            "Region Map Cursor": get_map_cursor(),
            "Text Printer #1": get_text_printer(0),
            "gMain.state": read_symbol("gMain", offset=0x438, size=1)[0],
            "Fade Active": is_fade_active(),
            "Play Time": get_play_time(),
        }

        if not context.rom.is_frlg:
            block_data["Local Time"] = get_clock_time()

        return block_data
