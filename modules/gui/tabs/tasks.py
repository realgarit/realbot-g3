# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.game.game import get_symbol_name_before
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.game.memory import (
    get_game_state,
    get_symbol,
    read_symbol,
    unpack_uint32,
    GameState,
)
from modules.core.tasks import (
    get_global_script_context,
    get_immediate_script_context,
    get_tasks,
    ScriptContext,
)

if TYPE_CHECKING:
    from modules.game.libmgba import LibmgbaEmulator


class TasksTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self._tv = FancyTreeview(frame, height=22, row=0)

        root.add(frame, text="Tasks")

    def update(self, emulator: "LibmgbaEmulator"):
        def get_callback_data(symbol_or_address: str | int, offset: int = 0) -> dict:
            if isinstance(symbol_or_address, int):
                pointer = symbol_or_address
            else:
                pointer = max(0, unpack_uint32(read_symbol(symbol_or_address, offset, size=4)))
            symbol_name = get_symbol_name_before(pointer, pretty_name=True)
            try:
                actual_symbol_start, _ = get_symbol(symbol_name)
                offset_from_symbol_start = hex(pointer - actual_symbol_start)
            except RuntimeError:
                actual_symbol_start = 0
                offset_from_symbol_start = ""
            return {
                "__value": symbol_name if pointer > 0 else "0x0",
                "Current Pointer": hex(pointer),
                "Function": symbol_name,
                "Actual Start of Function": hex(actual_symbol_start),
                "Offset": offset_from_symbol_start,
            }

        cb1_symbol = get_callback_data("gMain")
        cb2_symbol = get_callback_data("gMain", offset=4)

        def render_script_context(ctx: ScriptContext) -> dict | str:
            if ctx is None or not ctx.is_active:
                return "Not Active"

            stack_pointers = ctx.stack_pointers
            stack_symbols = ctx.stack

            stack: dict[str, str | dict] = (
                {"__value": "Empty"}
                if len(ctx.stack) == 1
                else {"__value": ", ".join(stack_symbols[: min(2, len(stack_symbols) - 1)])}
            )
            if len(stack_pointers) > 3:
                stack["__value"] += ", ..."
            for stack_index in range(len(stack_pointers)):
                stack[str(stack_index)] = get_callback_data(stack_pointers[stack_index])

            return {
                "__value": f"{ctx.script_function_name} / {ctx.native_function_name}",
                "Mode": ctx.mode,
                "Script Function": ctx.script_function_name,
                "Native Function": ctx.native_function_name,
                "Stack": stack,
                "Data": ctx.data,
                "Bytecode Pointer": hex(ctx.bytecode_pointer),
                "Native Pointer": hex(ctx.native_pointer),
            }

        data = {
            "Callback 1": cb1_symbol,
            "Callback 2": cb2_symbol,
            "Global Script Context": render_script_context(get_global_script_context()),
        }

        immediate_script_content = get_immediate_script_context()
        if immediate_script_content.is_active:
            data["Immediate Script Context"] = render_script_context(immediate_script_content)

        if get_game_state() == GameState.BATTLE:
            number_of_battlers = read_symbol("gBattlersCount", size=1)[0]

            current_battle_script_instruction = get_callback_data("gBattleScriptCurrInstr")
            main_battle_function = get_callback_data("gBattleMainFunc")
            player_controller_function = get_callback_data("gBattlerControllerFuncs", offset=0)

            data["Battle Context"] = {
                "__value": f"{main_battle_function['Function']} / {current_battle_script_instruction['Function']} / {player_controller_function['Function']}",
                "Battle Script": current_battle_script_instruction,
                "Main Battle Function": main_battle_function,
                "Battler Controller #1": player_controller_function,
            }

            for index in range(1, number_of_battlers):
                function = get_callback_data("gBattlerControllerFuncs", offset=4 * index)
                data["Battle Context"][f"Battler Controller #{index + 1}"] = function

        index = 0
        tasks = get_tasks()
        if tasks is not None:
            for task in get_tasks():
                short_task_data = task.data.rstrip(b"\00")
                if len(short_task_data) % 2 == 1:
                    short_task_data += b"\x00"
                data[task.symbol] = {
                    "__value": short_task_data.hex(" ", -2),
                    "Function": task.symbol,
                    "Pointer": hex(task.function_pointer),
                    "Priority": task.priority,
                    "Data": task.data.hex(" ", -2),
                }
                index += 1

        self._tv.update_data(data)
