# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.core.context import context
from modules.game.game_stats import GameStat, get_game_stat
from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview
from modules.items.items import get_item_bag, get_item_storage, get_pokeblocks
from modules.game.memory import game_has_started
from modules.player.player import AvatarFlags, get_player, get_player_avatar
from modules.pokemon.pokedex import get_pokedex
from modules.pokemon.pokemon_party import get_party
from modules.pokemon.pokemon_storage import get_pokemon_storage

if TYPE_CHECKING:
    from modules.game.libmgba import LibmgbaEmulator


class PlayerTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        root.add(frame, text="Player")

    def update(self, emulator: "LibmgbaEmulator"):
        if game_has_started():
            self._tv.update_data(self._get_data())
        else:
            self._tv.update_data({"": "Game has not been started yet."})

    def _get_data(self):
        player = get_player()
        player_avatar = get_player_avatar()
        try:
            party = get_party()
        except RuntimeError:
            party = []

        flags = {}
        active_flags = []
        for flag in AvatarFlags:
            flags[flag.name] = flag in player_avatar.flags
            if flag in player_avatar.flags:
                active_flags.append(flag.name)

        flags["__value"] = ", ".join(active_flags) if active_flags else "None"
        pokedex = get_pokedex()

        seen_species = pokedex.seen_species
        pokedex_seen = {"__value": len(seen_species)}
        for species in seen_species:
            pokedex_seen[species.national_dex_number] = species.name

        owned_species = pokedex.owned_species
        pokedex_owned = {"__value": len(owned_species)}
        for species in owned_species:
            pokedex_owned[species.national_dex_number] = species.name

        game_stats = {
            member.name: get_game_stat(member) for member in GameStat if member.value <= 49 or not context.rom.is_rs
        }
        result: dict[str, any] = {
            "Name": player.name,
            "Gender": player.gender,
            "Trainer ID": player.trainer_id,
            "Secret ID": player.secret_id,
            "Money": f"${player.money:,}",
            "Coins": f"{player.coins:,}",
            "Registered Item": player.registered_item.name if player.registered_item is not None else "None",
            "Map Group and Number": player_avatar.map_group_and_number,
            "Local Coordinates": player_avatar.local_coordinates,
            "Flags": flags,
            "On Bike": player_avatar.is_on_bike,
            "Running State": player_avatar.running_state.name,
            "Acro Bike State": player_avatar.acro_bike_state.name,
            "Tile Transition State": player_avatar.tile_transition_state.name,
            "Facing Direction": player_avatar.facing_direction,
            "Game Stats": game_stats,
            "Pokédex Seen": pokedex_seen,
            "Pokédex Owned": pokedex_owned,
        }

        for i in range(6):
            key = f"Party Pokémon #{i + 1}"
            if len(party) <= i or party[i].is_empty:
                result[key] = {"__value": "n/a"}
                continue

            result[key] = party[i]

        try:
            item_bag = get_item_bag()
            bag_data = {
                "Items": {"__value": f"{len(item_bag.items)}/{item_bag.items_size} Slots"},
                "Key Items": {"__value": f"{len(item_bag.key_items)}/{item_bag.key_items_size} Slots"},
                "Poké Balls": {"__value": f"{len(item_bag.poke_balls)}/{item_bag.poke_balls_size} Slots"},
                "TMs and HMs": {"__value": f"{len(item_bag.tms_hms)}/{item_bag.tms_hms_size} Slots"},
                "Berries": {"__value": f"{len(item_bag.berries)}/{item_bag.berries_size} Slots"},
            }
            total_slots = (
                item_bag.items_size
                + item_bag.key_items_size
                + item_bag.poke_balls_size
                + item_bag.tms_hms_size
                + item_bag.berries_size
            )
            used_slots = (
                len(item_bag.items)
                + len(item_bag.key_items)
                + len(item_bag.poke_balls)
                + len(item_bag.tms_hms)
                + len(item_bag.berries)
            )
            bag_data["__value"] = f"{used_slots}/{total_slots} Slots"
            for n, slot in enumerate(item_bag.items, start=1):
                bag_data["Items"][n] = f"{slot.quantity}× {slot.item.name}"
            for n, slot in enumerate(item_bag.key_items, start=1):
                bag_data["Key Items"][n] = f"{slot.quantity}× {slot.item.name}"
            for n, slot in enumerate(item_bag.poke_balls, start=1):
                bag_data["Poké Balls"][n] = f"{slot.quantity}× {slot.item.name}"
            for n, slot in enumerate(item_bag.tms_hms, start=1):
                bag_data["TMs and HMs"][n] = f"{slot.quantity}× {slot.item.name}"
            for n, slot in enumerate(item_bag.berries, start=1):
                bag_data["Berries"][n] = f"{slot.quantity}× {slot.item.name}"
            result["Item Bag"] = bag_data

            item_storage = get_item_storage()
            storage_data = {"__value": f"{len(item_storage.items)}/{item_storage.number_of_slots} Slots"}
            for n, slot in enumerate(item_storage.items, start=1):
                storage_data[n] = f"{slot.quantity}× {slot.item.name}"
            result["Item Storage"] = storage_data
        except (IndexError, KeyError):
            result["Item Storage"] = "???"

        if context.rom.is_rse:
            pokeblocks = get_pokeblocks()
            block_data = {"__value": f"{len(pokeblocks)}/40 slots"}
            for n in range(len(pokeblocks)):
                block = pokeblocks[n]
                block_data[n] = {
                    "__value": f"{block.colour.name}, Lv. {block.level}, Feel {block.feel}",
                    "Colour": block.colour.name,
                    "Feed": block.feel,
                    "Spicy": block.spicy,
                    "Bitter": block.bitter,
                    "Dry": block.dry,
                    "Sour": block.sour,
                    "Sweet": block.sweet,
                }
            result["Pokéblocks"] = block_data

        pokemon_storage = get_pokemon_storage()
        result["Pokemon Storage"] = {"__value": f"{pokemon_storage.pokemon_count} Pokémon"}
        for box in pokemon_storage.boxes:
            box_data = {"__value": f"{box.name} ({len(box)} Pokémon)"}
            for slot in box.slots:
                box_data[f"Row {slot.row}, Column {slot.column}"] = str(slot.pokemon)
            result["Pokemon Storage"][f"Box #{box.number + 1}"] = box_data

        return result
