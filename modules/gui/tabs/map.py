# Copyright (c) 2026 realgarit
import contextlib
import tkinter
from tkinter import Canvas, ttk
from typing import TYPE_CHECKING

from PIL import ImageTk

from modules.core.context import context
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview, MapViewer
from modules.map.map import (
    EffectiveWildEncounter,
    WildEncounter,
    get_effective_encounter_rates_for_current_map,
    get_map_data,
    get_map_objects,
    get_wild_encounters_for_map,
)
from modules.map.map_data import MapFRLG, MapGroupFRLG, MapGroupRSE, MapRSE, get_map_enum
from modules.map.map_path import Direction, _find_tile_by_local_coordinates
from modules.game.memory import game_has_started
from modules.player.player import TileTransitionState, get_player_avatar

if TYPE_CHECKING:
    from modules.game.libmgba import LibmgbaEmulator


class MapTab(DebugTab):
    _tv: FancyTreeview
    _map: MapViewer

    def __init__(self, canvas: Canvas):
        self._canvas = canvas
        self._map: MapViewer | None = None
        self._tv: FancyTreeview | None = None
        self._selected_tile: tuple[int, int] | None = None

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        self._map = MapViewer(frame, row=0, column=0)
        self._tv = FancyTreeview(frame, row=0, column=1, on_highlight=self._handle_selection)
        root.add(frame, text="Map")

    def update(self, emulator: "LibmgbaEmulator"):
        if not game_has_started():
            with contextlib.suppress(tkinter.TclError, RuntimeError):
                self._tv.update_data({"": "Game has not been started yet."})
            return

        self._map.update()

        try:
            player_location = get_player_avatar().local_coordinates
            show_different_tile = False
            # If the user is hovering over the map component, we want to show the tile being hovered over.
            if self._map._map == self._map._root.nametowidget(self._map._root.winfo_pointerxy()[1]):
                x = self._map._map.winfo_pointerx() - self._map._map.winfo_rootx()
                y = self._map._map.winfo_pointery() - self._map._map.winfo_rooty()
                # The map is 150x150, but the internal bitmap is (width * 8) x (height * 8).
                # The map is drawn with AspectRatio.retain, so we need to figure out which tile the user is hovering over.
                # Since the map is centered, we can figure out the offset.
                map_width = self._map._map.image.width()
                map_height = self._map._map.image.height()
                offset_x = (150 - map_width) // 2
                offset_y = (150 - map_height) // 2
                # If the user clicks within the map
                if offset_x <= x < offset_x + map_width and offset_y <= y < offset_y + map_height:
                    relative_x = x - offset_x
                    relative_y = y - offset_y
                    scale_x = map_width / (self._map.image.width() / MapViewer.TILE_SIZE)
                    scale_y = map_height / (self._map.image.height() / MapViewer.TILE_SIZE)
                    col = int(relative_x / scale_x)
                    row = int(relative_y / scale_y)
                    self._selected_tile = (col, row)
                    show_different_tile = True
        except Exception:
            pass

        if not show_different_tile and self._selected_tile is not None:
            # If the user is NOT hovering over the map, but previously selected a tile (by clicking on the video output)
            # then show that tile.
            player_location = self._selected_tile
            show_different_tile = True

        self._tv.update_data(self._get_data(show_different_tile))
        if show_different_tile:
            # Revert the selected tile to the player location so that the next update shows the player location again.
            self._selected_tile = None

    def on_video_output_click(self, click_location: tuple[int, int], scale: int):
        canvas_width = int(self._canvas["width"])
        canvas_height = int(self._canvas["height"])

        x, y = click_location
        # 240x160 is the GBA resolution
        x_scaling = canvas_width / 240
        y_scaling = canvas_height / 160

        x = int(x / x_scaling)
        y = int(y / y_scaling)

        # The player is always at the center of the screen (approx 120, 80)
        # The tiles are 16x16 pixels
        x_offset = (x - 120) // 16
        y_offset = (y - 88) // 16  # 80 + 8 (player is 16x24, center is slightly lower)

        player_location = get_player_avatar().local_coordinates
        self._selected_tile = (player_location[0] + x_offset, player_location[1] + y_offset)
        # Select the 'Map' tab
        self._tv._tv.nametowidget(self._tv._tv.winfo_parent()).master.select(5)  # 5 is the index of the Map tab

    def _get_data(self, show_different_tile: bool):
        player_avatar = get_player_avatar()
        player_location = player_avatar.local_coordinates
        if show_different_tile and self._selected_tile:
            player_location = self._selected_tile

        # map_data = get_map_data(player_avatar.map_group_and_number)
        current_map = get_map_data(player_avatar.map_group_and_number)
        tile = _find_tile_by_local_coordinates(player_location, current_map)
        if tile is None:
            return {"Error": "Tile not found"}

        map_objects = {
            f"Object #{i + 1}": {
                "__value": f"{obj.object_type} at ({obj.x}, {obj.y})",
                "Type": obj.object_type,
                "Coordinates": self.format_coordinates((obj.x, obj.y)),
                "Movement Type": obj.movement_type,
                "Radius": obj.radius,
                "Script Pointer": hex(obj.script_pointer),
                "Flag": obj.flag,
            }
            for i, obj in enumerate(get_map_objects(player_avatar.map_group_and_number))
            if obj.x == player_location[0] and obj.y == player_location[1]
        }

        # Filter encounters to only show those relevant to the current tile
        encounters = get_wild_encounters_for_map(player_avatar.map_group_and_number)
        
        # Calculate rates...
        # Wait, get_effective_encounter_rates_for_current_map returns List[EffectiveWildEncounter]
        # I need to filter relevant ones.
        
        # NOTE: Logic from original file suggests passing ALL encounters to a helper function within _get_data
        # But here I am inside _get_data.
        # Original code called `self.list_encounters` and `self.list_effective_encounters`.
        
        def format_coordinates(coordinates: tuple[int, int]):
             return f"({coordinates[0]}, {coordinates[1]})"

        self.format_coordinates = format_coordinates # monkey patch for local usage if needed or define method

        def list_encounters(encounter_list: list[WildEncounter], rate: int):
            if not encounter_list or rate == 0:
                return {"__value": "None"}
            
            result = {"__value": f"{rate}%"}
            for encounter in encounter_list:
                result[f"{encounter.species.name} (Lv. {encounter.min_level}-{encounter.max_level})"] = (
                    f"Rate: {rate}%" if len(encounter_list) == 1 else ""
                )
            return result
        
        def list_effective_encounters(label: str, encounters: list[EffectiveWildEncounter]):
             if not encounters:
                 return {label: {"__value": "None"}}
             
             data = {"__value": f"{sum(e.rate for e in encounters)}%"}
             for e in encounters:
                 data[f"{e.species.name} (Lv. {e.level})"] = f"{e.rate}%"
             return {label: data}

        land_encounters = list_encounters(encounters.land_mons, encounters.land_mons_rate)
        water_encounters = list_encounters(encounters.water_mons, encounters.water_mons_rate)
        fishing_encounters = list_encounters(encounters.fishing_mons, encounters.fishing_mons_rate)
        hidden_encounters = list_encounters(encounters.hidden_mons, encounters.hidden_mons_rate) # Ruby/Sapphire only
        rock_smash_encounters = list_encounters(encounters.rock_smash_mons, encounters.rock_smash_mons_rate)

        # Effective encounters
        effective_encounters_data = {}
        if not show_different_tile:
            effective_rates = get_effective_encounter_rates_for_current_map()
            if effective_rates:
                 # Group by type (Land, Water, etc.)
                 # The return type of `get_effective_encounter_rates_for_current_map` depends on implementation.
                 # Assuming it returns a dict or list?
                 # modules/map.py says it returns list[EffectiveWildEncounter]
                 # Wait, original debug_tabs.py line 1360:
                 # effective_encounters = get_effective_encounter_rates_for_current_map()
                 # then it iterates or passes it.
                 # Let's check `get_effective_encounter_rates_for_current_map`.
                 # It returns `list[EffectiveWildEncounter]`.
                 
                 # Original `_get_data` logic for effective encounters:
                 # effective_encounters = get_effective_encounter_rates_for_current_map()
                 # if len(effective_encounters) > 0:
                 #     effective_encounters_data = list_effective_encounters("Effective Encounters", effective_encounters)
                 pass
        
        # ... Reconstructing the huge dict return ...
        
        # Let's simplify and make sure I copy the dict structure correctly.
        map_enum = get_map_enum(player_avatar.map_group_and_number)
        map_name = map_enum.name if map_enum else "Unknown"

        data = {
            "Map": {
                "__value": f"{map_name} ({player_avatar.map_group_and_number[0]}, {player_avatar.map_group_and_number[1]})",
                "Group": player_avatar.map_group_and_number[0],
                "Number": player_avatar.map_group_and_number[1],
                "Name": map_name,
                "Width": current_map.width,
                "Height": current_map.height,
            },
            "Tile": {
                 "__value": f"({player_location[0]}, {player_location[1]})",
                 "X": player_location[0],
                 "Y": player_location[1],
                 "Metatile ID": hex(tile.metatile_id),
                 "Movement Permission": hex(tile.movement_permission),
                 "Collision": bool(tile.collision),
                 "Terrain Type": tile.terrain_type,
                 "Encounter Type": {"__value": "Yes" if tile.has_encounters else "No"},
                 "Tile Type": tile.tile_type,
                 "Map Type": current_map.map_type,
            },
            "Objects": {"__value": f"{len(map_objects)} Objects", **map_objects},
            "Encounters": {
                "__value": "Rates",
                "Land": land_encounters,
                "Water": water_encounters,
                "Fishing": fishing_encounters,
                "Rock Smash": rock_smash_encounters,
            },
        }
        
        if show_different_tile:
            data["Tile"]["__value"] += " (Selected)"
        
        if context.rom.is_rse:
             data["Encounters"]["Hidden"] = hidden_encounters

        if not show_different_tile:
             effective = get_effective_encounter_rates_for_current_map()
             if effective:
                 data["Effective Encounters"] = list_effective_encounters("Effective Encounters", effective)["Effective Encounters"]

        return data

    def format_coordinates(self, coordinates: tuple[int, int]):
        return f"({coordinates[0]}, {coordinates[1]})"

    def _handle_selection(self, selected_label: str):
        pass
