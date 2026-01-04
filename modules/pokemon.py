# Copyright (c) 2026 realgarit
import contextlib
from dataclasses import dataclass
from typing import Literal

from modules.context import context
from modules.game import decode_string
from modules.items import get_item_by_name
from modules.memory import pack_uint32, read_symbol, unpack_uint32, unpack_uint16
from modules.pokemon_constants import (
    HIDDEN_POWER_MAP,
    LOCATION_MAP,
    POKEMON_DATA_SUBSTRUCTS_ORDER,
)
from modules.pokemon_data import (
    Ability,
    ContestConditions,
    HeldItem,
    LearnedMove,
    LevelUpType,
    Marking,
    Move,
    Nature,
    OriginalTrainer,
    PokerusStatus,
    Species,
    SpeciesEvolution,
    SpeciesLevelUpMove,
    SpeciesMoveLearnset,
    SpeciesTmHmMove,
    StatsValues,
    StatusCondition,
    Type,
    _to_dict_helper,
    get_ability_by_index,
    get_ability_by_name,
    get_move_by_index,
    get_move_by_name,
    get_nature_by_index,
    get_nature_by_name,
    get_species_by_index,
    get_species_by_name,
    get_species_by_national_dex,
    get_type_by_index,
    get_type_by_name,
    get_unown_index_by_letter,
    get_unown_letter_by_index,
)
from modules.roms import ROMLanguage


@dataclass
class Pokemon:
    """
    Represents an individual Pokémon.

    The only real data in here is the `self.data` property, which contains the 100-byte (party Pokémon)
    or 80-byte (box Pokémon) string of data that everything else can be computed from.

    Everything else (nickname, IVs, ...) is computed on the fly using the getters.
    """

    data: bytes

    def __init__(self, data: bytes):
        self.data = data

    def __eq__(self, other):
        if not isinstance(other, Pokemon):
            return NotImplemented
        return self.data == other.data

    def __ne__(self, other):
        if not isinstance(other, Pokemon):
            return NotImplemented
        return self.data != other.data

    def _decrypted_data(self) -> bytes:
        """
        Returns the decrypted Pokémon data and also puts the substructures in a consistent order.

        For more information regarding encryption and substructure ordering, see:
        https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)

        IMPORTANT:
        This does NOT handle the fact that moving substructures around changes the checksum!
        This function is purely for reading stats. Do NOT use the output of this function to
        create a new .pk3 file!

        It puts the substructures in the same order as they are listed on Bulbapedia, to make working
        with offsets a bit easier.

        :return: The decrypted and re-ordered data for this Pokémon.
        """
        personality_value = unpack_uint32(self.data[0:4])
        # Box Pokémon (80 bytes) do not track current HP, level, status condition etc.
        # Party Pokémon (100 bytes) do.
        # We always return the 80 bytes of base data, and if the data is a party Pokémon,
        # we append the 20 bytes of stats at the end.
        is_party_pokemon = len(self.data) == 100

        data = bytearray(self.data)
        trainer_id = unpack_uint32(data[4:8])
        decryption_key = trainer_id ^ personality_value

        # The data is divided into 4 substructures of 12 bytes each.
        # The offset of these substructures (relative to the start of the data, after PID and OTID)
        # depends on the personality value.
        order_index = personality_value % 24
        order = POKEMON_DATA_SUBSTRUCTS_ORDER[order_index]

        decrypted_data = bytearray(80)
        decrypted_data[0:8] = data[0:8]  # Copy PID and OTID
        decrypted_data[32:80] = data[32:80]  # Copy nickname, OT name, markings, checksum and padding

        # Decrypt the substructures and put them in the correct order
        for i in range(4):
            source_offset = 32 + (order[i] * 12)
            for j in range(0, 12, 4):
                value = unpack_uint32(data[source_offset + j : source_offset + j + 4])
                value ^= decryption_key
                decrypted_data[32 + (i * 12) + j : 32 + (i * 12) + j + 4] = pack_uint32(value)

        # Move the substructures from the end of the data to the middle, where they belong
        decrypted_data[8:56] = decrypted_data[32:80]
        # And move the nickname, OT name, etc. to the end
        decrypted_data[56:80] = data[8:32]

        if is_party_pokemon:
            decrypted_data.extend(data[80:100])

        return bytes(decrypted_data)

    def to_pk3(self) -> bytes:
        """
        Returns the decrypted Pokémon data in export format.
        The substructures are decrypted and reordered to standard order (0, 1, 2, 3),
        and the checksum is recalculated from the decrypted data.

        This format is compatible with PKHeX and other save editors.
        Note that this only exports the 80-byte base data, so level, current, HP, etc. are lost.
        This is unavoidable because the file format does not support storing these values.
        For more info, see:
        https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)#Format

        :return: The decrypted data in export format.
        """
        data = bytearray(self._decrypted_data())
        # First 32 bytes (PID, OTID, Nickname, Language, OT Name, etc) are already correct
        # Substructures need to be checked; _decrypted_data puts them in order 0, 1, 2, 3
        # so they should be correct too.

        # We need to recalculate the checksum, because _decrypted_data might have moved
        # things around, invalidating the original checksum.
        checksum = 0
        for i in range(0, 48, 2):  # 48 bytes is the length of the 4 substructures (4 * 12)
            checksum += unpack_uint16(data[8 + i : 8 + i + 2])
            checksum &= 0xFFFF

        # Checksum is stored at offset 28 in the 80-byte structure
        # (which is offset 0x1C)
        # However, in our decrypted format:
        # 0-8: PID, OTID
        # 8-56: Substructures 0-3
        # 56-66: Nickname
        # 66-67: Language
        # 67: Egg name flag
        # 68-75: OT Name
        # 75: Markings
        # 76-78: Checksum
        # 78-80: Unused
        data[76:78] = checksum.to_bytes(2, byteorder="little")
        return bytes(data[:80])

    def _character_set(self) -> str:
        """
        Figures out which character set needs to be used for decoding nickname and
        original trainer name of this Pokémon.
        :return: The character table name as supported by `DecodeString()`
        """
        if self.language == ROMLanguage.Japanese:
            return "japanese"
        else:
            return "english"

    @property
    def calculate_checksum(self) -> int:
        data = self._decrypted_data()
        checksum = 0
        for i in range(0, 48, 2):
            checksum += unpack_uint16(data[8 + i : 8 + i + 2])
            checksum &= 0xFFFF
        return checksum

    @property
    def get_data_checksum(self) -> int:
        data = self._decrypted_data()
        return unpack_uint16(data[76:78])

    @property
    def is_valid(self) -> bool:
        return self.calculate_checksum == self.get_data_checksum

    @property
    def is_empty(self) -> bool:
        """
        Since many places in memory _might_ contain a Pokémon but also might not (all zeros or something),
        this checks whether a given block of data is actually a Pokémon the same way the game does.
        :return: Whether the data represents a Pokémon or is just an empty slot.
        """
        if len(self.data) < 80:
            return True

        if self.species.index == 0:
            return True

        return self.personality_value == 0

    @property
    def personality_value(self) -> int:
        return unpack_uint32(self.data[0:4])

    @property
    def original_trainer(self) -> OriginalTrainer:
        ptid = unpack_uint32(self.data[4:8])
        id = ptid & 0xFFFF
        secret_id = ptid >> 16

        data = self._decrypted_data()
        name = decode_string(data[68:75], self._character_set())
        # The gender of the original trainer is stored in the last bit of the
        # 'Egg Name' byte (offset 67)
        gender_byte = data[67]
        gender = "female" if (gender_byte & 128) else "male"
        return OriginalTrainer(id, secret_id, name, gender)  # type: ignore

    @property
    def nickname(self) -> str:
        data = self._decrypted_data()
        return decode_string(data[56:66], self._character_set())

    @property
    def name(self) -> str:
        if self.is_egg:
            return "Egg"

        nickname = self.nickname
        if nickname == "":
            return self.species.name
        else:
            return nickname

    @property
    def language(self) -> ROMLanguage:
        data = self._decrypted_data()
        lang_id = data[66]
        try:
            return ROMLanguage(lang_id)
        except ValueError:
            return ROMLanguage.English

    @property
    def is_egg(self) -> bool:
        data = self._decrypted_data()
        ivs_egg_ability = unpack_uint32(data[36:40])
        return bool((ivs_egg_ability >> 30) & 1)

    @property
    def markings(self) -> list[Marking]:
        data = self._decrypted_data()
        markings_byte = data[75]
        result = []
        if markings_byte & 1:
            result.append(Marking.Circle)
        if markings_byte & 2:
            result.append(Marking.Square)
        if markings_byte & 4:
            result.append(Marking.Triangle)
        if markings_byte & 8:
            result.append(Marking.Heart)
        return result

    @property
    def species(self) -> Species:
        data = self._decrypted_data()
        species_id = unpack_uint16(data[8:10])
        if self.is_egg:
            # For eggs, the species ID is that of the Pokémon inside the egg,
            # but usually we want to treat it as an egg (species 0? or separate check?)
            # The game uses species ID to determine sprite etc.
            pass

        return get_species_by_index(species_id)

    @property
    def held_item(self) -> any:  # imports.Item caused circular import, using 'any' or logic inside
        data = self._decrypted_data()
        item_id = unpack_uint16(data[10:12])
        if item_id == 0:
            return None
        # Lazy import to avoid circular dependency
        from modules.items import get_item_by_index

        return get_item_by_index(item_id)

    @property
    def experience(self) -> int:
        data = self._decrypted_data()
        return unpack_uint32(data[12:16])

    @property
    def pp_bonuses(self) -> list[int]:
        data = self._decrypted_data()
        pp_bonuses_byte = data[16]
        return [
            pp_bonuses_byte & 3,
            (pp_bonuses_byte >> 2) & 3,
            (pp_bonuses_byte >> 4) & 3,
            (pp_bonuses_byte >> 6) & 3,
        ]

    @property
    def friendship(self) -> int:
        data = self._decrypted_data()
        return data[17]

    @property
    def moves(self) -> list[LearnedMove | None]:
        data = self._decrypted_data()
        result = []
        for i in range(4):
            move_id = unpack_uint16(data[20 + (i * 2) : 22 + (i * 2)])
            pp = data[28 + i]
            pp_ups = self.pp_bonuses[i]

            if move_id == 0:
                result.append(None)
            else:
                result.append(LearnedMove.create(get_move_by_index(move_id), pp, pp_ups))
        return result

    @property
    def evs(self) -> StatsValues:
        data = self._decrypted_data()
        return StatsValues(
            hp=data[32],
            attack=data[33],
            defence=data[34],
            speed=data[35],
            special_attack=data[36],
            special_defence=data[37],
        )

    @property
    def contest_conditions(self) -> ContestConditions:
        data = self._decrypted_data()
        return ContestConditions(
            coolness=data[38],
            beauty=data[39],
            cuteness=data[40],
            smartness=data[41],
            toughness=data[42],
            feel=data[43],
        )

    @property
    def pokerus_status(self) -> PokerusStatus | None:
        data = self._decrypted_data()
        pokerus_byte = data[44]
        if pokerus_byte == 0:
            return None
        return PokerusStatus(strain=pokerus_byte >> 4, days_remaining=pokerus_byte & 0xF)

    @property
    def met_location(self) -> str:
        data = self._decrypted_data()
        location_id = data[45]
        if location_id < len(LOCATION_MAP):
            return LOCATION_MAP[location_id]
        else:
            return f"Unknown ({location_id})"

    @property
    def origin_info(self) -> dict:
        data = self._decrypted_data()
        origins_byte = unpack_uint16(data[46:48])
        return {
            "level_met": origins_byte & 0x7F,
            "game_of_origin": ROMLanguage((origins_byte >> 7) & 0xF),  # Actually game ID, not language
            "pokeball": (origins_byte >> 11) & 0xF,
            "ot_gender": "female" if (origins_byte >> 15) & 1 else "male",
        }

    @property
    def ivs(self) -> StatsValues:
        data = self._decrypted_data()
        ivs_egg_ability = unpack_uint32(data[48:52])
        return StatsValues(
            hp=ivs_egg_ability & 31,
            attack=(ivs_egg_ability >> 5) & 31,
            defence=(ivs_egg_ability >> 10) & 31,
            speed=(ivs_egg_ability >> 15) & 31,
            special_attack=(ivs_egg_ability >> 20) & 31,
            special_defence=(ivs_egg_ability >> 25) & 31,
        )

    @property
    def ribbons(self):
        data = self._decrypted_data()
        result = {}
        result["cool"] = data[52] & 7
        result["beauty"] = (data[52] >> 3) & 7
        result["cute"] = (data[52] >> 6) & 1
        # ... logic for other ribbons ...
        return result

    @property
    def ability(self) -> Ability | None:
        data = self._decrypted_data()
        ivs_egg_ability = unpack_uint32(data[48:52])
        ability_bit = (ivs_egg_ability >> 31) & 1
        return self.species.abilities[ability_bit] if len(self.species.abilities) > ability_bit else None

    @property
    def level(self) -> int:
        if len(self.data) == 100:
            return self.data[84]
        else:
            return self.species.level_up_type.get_level_from_total_experience(self.experience)

    @property
    def stats(self) -> StatsValues:
        if len(self.data) == 100:
            return StatsValues(
                hp=unpack_uint16(self.data[86:88]),
                attack=unpack_uint16(self.data[88:90]),
                defence=unpack_uint16(self.data[90:92]),
                speed=unpack_uint16(self.data[92:94]),
                special_attack=unpack_uint16(self.data[94:96]),
                special_defence=unpack_uint16(self.data[96:98]),
            )
        else:
            if self.species.name == "Shedinja":
                # Shedinja always has 1 HP
                hp = 1
            else:
                # Calculate stats
                return StatsValues.calculate(self.species, self.ivs, self.evs, self.nature, self.level)
            return StatsValues.calculate(self.species, self.ivs, self.evs, self.nature, self.level)

    @property
    def current_hp(self) -> int:
        if len(self.data) == 100:
            return unpack_uint16(self.data[86:88])
        else:
            return self.stats.hp

    @property
    def current_hp_percentage(self) -> float:
        if self.stats.hp == 0:
            return 0.0
        return (self.current_hp / self.stats.hp) * 100

    @property
    def status_condition(self) -> StatusCondition:
        if len(self.data) == 100:
            return StatusCondition.from_bitfield(unpack_uint32(self.data[80:84]))
        else:
            return StatusCondition.Healthy

    @property
    def nature(self) -> Nature:
        return get_nature_by_index(self.personality_value % 25)

    @property
    def gender(self) -> str:
        gender_threshold = self.species.gender_ratio
        if gender_threshold == 255:
            return "Genderless"
        elif gender_threshold == 254:
            return "Female"
        elif gender_threshold == 0:
            return "Male"
        else:
            gender_value = self.personality_value & 0xFF
            return "Female" if gender_value >= gender_threshold else "Male"

    @property
    def shiny_value(self) -> int:
        trainer_id = self.original_trainer.id
        secret_id = self.original_trainer.secret_id
        personality_value = self.personality_value
        p1 = (personality_value >> 16) & 0xFFFF
        p2 = personality_value & 0xFFFF
        return trainer_id ^ secret_id ^ p1 ^ p2

    @property
    def is_shiny(self) -> bool:
        return self.shiny_value < 8

    @property
    def is_anti_shiny(self) -> bool:
        """
        An 'Anti-Shiny' is a Pokémon that WOULD be shiny, if the PID and Trainer ID
        were XOR'd differently.
        Specifically, (TID ^ PID_HI) ^ (SID ^ PID_LO) < 8.
        This is mostly just a fun curiosity.
        """
        trainer_id = self.original_trainer.id
        secret_id = self.original_trainer.secret_id
        personality_value = self.personality_value
        p1 = (personality_value >> 16) & 0xFFFF
        p2 = personality_value & 0xFFFF
        return (trainer_id ^ p1) ^ (secret_id ^ p2) < 8

    @property
    def hidden_power_type(self) -> Type:
        t = 0
        for i, stat in enumerate(["hp", "attack", "defence", "speed", "special_attack", "special_defence"]):
            if self.ivs[stat] & 1:
                t += 1 << i
        type_index = (t * 15) // 63
        return get_type_by_name(HIDDEN_POWER_MAP[type_index])

    @property
    def hidden_power_damage(self) -> int:
        d = 0
        for i, stat in enumerate(["hp", "attack", "defence", "speed", "special_attack", "special_defence"]):
            if (self.ivs[stat] >> 1) & 1:
                d += 1 << i
        return (d * 40) // 63 + 30

    @property
    def unown_letter(self) -> str:
        if self.species.name != "Unown":
            return ""

        personality_value = self.personality_value
        letter_index = (
            ((personality_value >> 24) & 3)
            | ((personality_value >> 16) & 3) << 2
            | ((personality_value >> 8) & 3) << 4
            | (personality_value & 3) << 6
        ) % 28

        return get_unown_letter_by_index(letter_index)

    @property
    def wurmple_evolution(self) -> str:
        if self.species.name != "Wurmple":
            return ""

        personality_value = self.personality_value
        return "Silcoon" if (personality_value >> 16) % 10 < 5 else "Cascoon"

    @property
    def species_name_for_stats(self) -> str:
        if self.species.name == "Unown":
            return f"Unown ({self.unown_letter})"
        return self.name

    def __str__(self):
        return f"{self.name} (Lv. {self.level})"

    def to_dict(self) -> dict:
        return _to_dict_helper(self)


def get_opponent() -> Pokemon | None:
    """
    :return: The first Pokémon of the opponent's party, or None if there is no active opponent.
    """
    from modules.pokemon_party import get_opponent_party

    opponent_party = get_opponent_party()
    if opponent_party is None:
        return None
    else:
        return opponent_party[0]


last_opid = pack_uint32(0)  # ReadSymbol('gEnemyParty', size=4)


def clear_opponent() -> None:
    global last_opid
    last_opid = pack_uint32(0)


def opponent_changed() -> bool:
    """
    Checks if the current opponent/encounter from `gEnemyParty` has changed since the function was last called.
    Very fast way to check as this only reads the first 4 bytes (PID) and does not decode the Pokémon data.

    :return: True if opponent changed, otherwise False (bool)
    """
    try:
        global last_opid
        opponent_pid = read_symbol("gEnemyParty", size=4)
        battle_type = unpack_uint32(read_symbol("gBattleTypeFlags", size=0x04))
        trainer_or_tutorial = (1 << 3) | (1 << 9)
        if opponent_pid != last_opid and opponent_pid != b"\x00\x00\x00\x00" and battle_type & trainer_or_tutorial:
            last_opid = opponent_pid
            return True
        else:
            return False
    except SystemExit:
        raise
    except Exception:
        return False


def pokemon_has_usable_damaging_move(pokemon: Pokemon) -> bool:
    """
    Checks if the given Pokémon has at least one usable attacking move.
    Returns True if a usable move is found; otherwise, False.
    """
    return any(
        move is not None and move.move.base_power > 0 and move.move.name not in context.config.battle.banned_moves
        for move in pokemon.moves
    )


def parse_pokemon(data: bytes) -> Pokemon:
    return Pokemon(data)
