# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.battle_state import battle_is_active, get_battle_state
from modules.game import decode_string, get_symbol_name, get_symbol_name_before
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.memory import (
    game_has_started,
    get_symbol,
    read_symbol,
    unpack_uint16,
    unpack_uint32,
)
from modules.pokemon import get_species_by_index

if TYPE_CHECKING:
    from modules.libmgba import LibmgbaEmulator


class BattleTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Battle")

    def update(self, emulator: "LibmgbaEmulator"):
        if game_has_started():
            self._tv.update_data(self._get_data())
        else:
            self._tv.update_data({"": "Game has not been started yet."})

    def _get_data(self):
        data = read_symbol("gBattleResults")
        currins = unpack_uint32(read_symbol("gBattleScriptCurrInstr", size=4))

        return {
            "State": get_battle_state() if battle_is_active() else None,
            "Current Instruction": hex(currins),
            "Instruction Symbol": get_symbol_name(currins, True),
            "Instruction Symbol #2": get_symbol_name_before(currins, True),
            "Instruction Offset": (
                0 if currins == 0 else hex(currins - get_symbol(get_symbol_name_before(currins, True))[0])
            ),
            "Player Faint Counter": int(data[0]),
            "Opponent Faint Counter": int(data[1]),
            "Player Switch Counter": int(data[2]),
            "Count Healing Items used": int(data[3]),
            "Player Mon Damaged": bool(data[5] & 0x1),  # :1;   // 0x5
            "Master Ball used": bool(data[5] & 0x2),  # :1;     // 0x5
            "Caught Mon Ball used": int(data[5] & 0x30),  # :4; // 0x5
            "Wild Mon was Shiny": bool(data[5] & 0x40),  # :1;  // 0x5
            "Count Revives used": int(data[4]),
            "Player Mon 1 Species": unpack_uint16(data[6:8]),
            "Player Mon 1 Name": decode_string(data[8:19]),  # SpeciesName(battleResult.playerMon1Species)
            "Battle turn Counter": int(data[19]),
            "Player Mon 2 Species": unpack_uint16(data[38:40]),
            "Player Mon 2 Name": decode_string(data[20:31]),
            "PokeBall Throws": int(data[31]),
            "Last Opponent Species": unpack_uint16(data[32:34]),
            "Last Opponent Name": get_species_by_index(unpack_uint16(data[32:34])).name,
            "Last used Move Player": unpack_uint16(data[34:36]),
            "Last used Move Opponent": unpack_uint16(data[36:38]),
            "Caught Mon Species": unpack_uint16(data[40:42]),
            "Caught Mon Name": decode_string(data[42:53]),
            "Catch Attempts": int(data[54]),
        }
