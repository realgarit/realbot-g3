# Copyright (c) 2026 realgarit
import contextlib
import json
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Literal

from modules.items.items import Item, get_item_by_name, get_item_by_move_id
from modules.core.runtime import get_data_path
from modules.pokemon.pokemon_constants import DATA_DIRECTORY


class Type:
    """
    This represents an elemental type such as Fight, Electric, etc.
    """

    def __init__(self, index: int, name: str):
        self.index: int = index
        self.name: str = name
        self._effectiveness: dict["Type", float] = {}

    def set_effectiveness(self, other_type: "Type", effectiveness: float):
        self._effectiveness[other_type] = effectiveness

    def get_effectiveness_against(self, other_type: "Type") -> float:
        return self._effectiveness.get(other_type, 1)

    @property
    def is_physical(self) -> bool:
        return self.index < 9

    @property
    def is_special(self) -> bool:
        return self.index >= 9

    @property
    def kind(self) -> str:
        return "Physical" if self.is_physical else "Special"

    @property
    def safe_name(self) -> str:
        return "Unknown" if self.name == "???" else self.name

    def __str__(self):
        return self.name


@dataclass
class Move:
    """
    This represents a battle move, but not the connection to any particular Pokémon.
    Think of it as the 'move species'.
    """

    index: int
    name: str
    description: str
    type: Type
    accuracy: float
    # This is the accuracy for a secondary effect, such as optional
    # status changes etc.
    secondary_accuracy: float
    pp: int
    priority: int
    base_power: int
    effect: str
    target: str
    makes_contact: bool
    is_sound_move: bool
    affected_by_protect: bool
    affected_by_magic_coat: bool
    affected_by_snatch: bool
    usable_with_mirror_move: bool
    affected_by_kings_rock: bool
    tm_hm: Item | None

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Move":
        return Move(
            index=index,
            name=data["name"],
            description=data["localised_descriptions"]["E"],
            type=get_type_by_name(data["type"]),
            accuracy=float(data["accuracy"]),
            secondary_accuracy=float(data["secondary_accuracy"]),
            pp=data["pp"],
            priority=data["priority"],
            base_power=data["base_power"],
            effect=data["effect"],
            target=data["target"],
            makes_contact=data["makes_contact"],
            is_sound_move=data["is_sound_move"],
            affected_by_protect=data["affected_by_protect"],
            affected_by_magic_coat=data["affected_by_magic_coat"],
            affected_by_snatch=data["affected_by_snatch"],
            usable_with_mirror_move=data["usable_with_mirror_move"],
            affected_by_kings_rock=data["affected_by_kings_rock"],
            tm_hm=get_item_by_name(data["tm_hm"]) if data["tm_hm"] is not None else None,
        )


@dataclass
class LearnedMove:
    """
    This represents a move slot for an individual Pokémon.
    """

    move: Move
    total_pp: int
    pp: int
    pp_ups: int

    @classmethod
    def create(cls, move: Move, remaining_pp: int | None = None, pp_ups: int = 0) -> "LearnedMove":
        total_pp = move.pp + ((move.pp * 20 * pp_ups) // 100)
        remaining_pp = total_pp if remaining_pp is None else min(total_pp, remaining_pp)
        return LearnedMove(move=move, total_pp=total_pp, pp=remaining_pp, pp_ups=pp_ups)

    def added_pps(self) -> int:
        return self.total_pp - self.move.pp

    def __str__(self):
        return f"{self.move.name} ({self.pp} / {self.total_pp})"


@dataclass
class StatsValues:
    """
    A collection class for all 6 stats; can be used as a convenience thing wherever a list of
    stats is required (IVs, EVs, Pokémon stats, EV yields, ...)
    """

    hp: int
    attack: int
    defence: int
    speed: int
    special_attack: int
    special_defence: int

    @classmethod
    def from_dict(cls, data: dict) -> "StatsValues":
        return StatsValues(
            data.get("hp", 0),
            data.get("attack", 0),
            data.get("defence", 0),
            data.get("speed", 0),
            data.get("special_attack", 0),
            data.get("special_defence", 0),
        )

    def __getitem__(self, item):
        return self.__getattribute__(item)

    @classmethod
    def calculate(
        cls, species: "Species", ivs: "StatsValues", evs: "StatsValues", nature: "Nature", level: int
    ) -> "StatsValues":
        """
        Re-calculates the current effective stats of a Pokémon. This is needed for boxed
        Pokémon, that do not store their current stats anywhere.
        :param species:
        :param ivs:
        :param evs:
        :param nature:
        :param level:
        :return: The calculated set of battle stats for the Pokémon
        """
        if species.national_dex_number == 292:
            # Shedinja always has 1 HP
            hp = 1
        else:
            hp = ((2 * species.base_stats.hp + ivs.hp + (evs.hp // 4)) * level) // 100 + 10 + level

        stats = {
            i: (((2 * species.base_stats[i] + ivs[i] + (evs[i] // 4)) * level) // 100 + 5) * nature.modifiers[i]
            for i in [
                "attack",
                "defence",
                "speed",
                "special_attack",
                "special_defence",
            ]
        }
        return cls(
            hp=int(hp),
            attack=int(stats["attack"]),
            defence=int(stats["defence"]),
            speed=int(stats["speed"]),
            special_attack=int(stats["special_attack"]),
            special_defence=int(stats["special_defence"]),
        )

    def sum(self) -> int:
        return self.hp + self.attack + self.defence + self.speed + self.special_attack + self.special_defence


@dataclass
class ContestConditions:
    """
    Represents the stats that are being used in the Pokémon Contest, equivalent to `StatsValues`.
    """

    coolness: int
    beauty: int
    cuteness: int
    smartness: int
    toughness: int
    feel: int


@dataclass
class HeldItem:
    """
    Represents a possible held item for a Pokémon encounter, along with the probability of it
    being held.
    """

    item: Item
    probability: float


@dataclass
class Nature:
    """
    Represents a Pokémon nature and its stats modifiers, along with preferred and disliked Pokéblock flavors.
    """

    index: int
    name: str
    modifiers: dict[str, float]

    def __str__(self):
        return self.name

    @property
    def name_with_modifiers(self) -> str:
        increased_stat = None
        decreased_stat = None
        for stat in self.modifiers:
            if self.modifiers[stat] > 1:
                increased_stat = stat
            elif self.modifiers[stat] < 1:
                decreased_stat = stat

        if increased_stat is None or decreased_stat is None or increased_stat == decreased_stat:
            return f"{self.name} (neutral)"

        stat_name_map = {
            "attack": "Atk",
            "defence": "Def",
            "speed": "Speed",
            "special_attack": "SpAtk",
            "special_defence": "SpDef",
        }
        return f"{self.name} (+{stat_name_map[increased_stat]}, -{stat_name_map[decreased_stat]})"

    @property
    def pokeblock_preferences(self) -> dict[str, str | None]:
        flavour_map = {
            "spicy": "attack",
            "dry": "special_attack",
            "sweet": "speed",
            "bitter": "special_defence",
            "sour": "defence",
        }
        liked = None
        disliked = None
        for flavour, stat_name in flavour_map.items():
            if self.modifiers[stat_name] > 1:
                liked = flavour
            elif self.modifiers[stat_name] < 1:
                disliked = flavour
        return {"liked": liked, "disliked": disliked}

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Nature":
        return Nature(
            index=index,
            name=data["name"],
            modifiers={
                "attack": data["attack_modifier"],
                "defence": data["defence_modifier"],
                "speed": data["speed_modifier"],
                "special_attack": data["special_attack_modifier"],
                "special_defence": data["special_defence_modifier"],
            },
        )


@dataclass
class Ability:
    index: int
    name: str

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Ability":
        return Ability(index=index, name=data["name"])


class LevelUpType(Enum):
    MediumFast = "Medium Fast"
    Erratic = "Erratic"
    Fluctuating = "Fluctuating"
    MediumSlow = "Medium Slow"
    Fast = "Fast"
    Slow = "Slow"

    def get_experience_needed_for_level(self, level: int) -> int:
        """
        Calculates how much total experience is needed to reach a given level. The formulas here
        are taken straight from the decompliation project.
        :param level: The level to check for
        :return: The number of EXP required to reach that level
        """
        if level == 0:
            return 0
        elif level == 1:
            return 1
        elif self == LevelUpType.MediumSlow:
            return ((6 * (level**3)) // 5) - (15 * (level**2)) + (100 * level) - 140
        elif self == LevelUpType.Erratic:
            if level <= 50:
                return (100 - level) * (level**3) // 50
            elif level <= 68:
                return (150 - level) * (level**3) // 100
            elif level <= 98:
                return ((1911 - 10 * level) // 3) * (level**3) // 500
            else:
                return (160 - level) * (level**3) // 100
        elif self == LevelUpType.Fluctuating:
            if level <= 15:
                return ((level + 1) // 3 + 24) * (level**3) // 50
            elif level <= 36:
                return (level + 14) * (level**3) // 50
            else:
                return ((level // 2) + 32) * (level**3) // 50
        elif self == LevelUpType.MediumFast:
            return level**3
        elif self == LevelUpType.Slow:
            return (5 * (level**3)) // 4
        elif self == LevelUpType.Fast:
            return (4 * (level**3)) // 5

    def get_level_from_total_experience(self, total_experience: int) -> int:
        """
        Calculates which level a Pokémon should be, given a number of total EXP.
        This is required for box Pokémon, that do not actually store their level.
        :param total_experience: Total number of experience points
        :return: The level a Pokémon would have with that amount of EXP
        """
        level = 0
        while level < 100 and total_experience >= self.get_experience_needed_for_level(level + 1):
            level += 1
        return level


@dataclass
class SpeciesLevelUpMove:
    level: int
    move: Move

    def __str__(self):
        return f"{self.move.name} at Lv. {self.level}"


@dataclass
class SpeciesTmHmMove:
    item: Item
    move: Move

    def __str__(self):
        return f"{self.item.name} ({self.move.name})"

    def debug_dict_value(self):
        return {
            "item": self.item.name,
            "move": self.move.name,
        }


@dataclass
class SpeciesMoveLearnset:
    level_up: list[SpeciesLevelUpMove]
    tm_hm: list[SpeciesTmHmMove]
    tutor: list[Move]
    egg: list[Move]

    def debug_dict_value(self):
        return {
            "level_up": [f"{entry.move.name} at Lv. {entry.level}" for entry in self.level_up],
            "tm_hm": [f"{entry.item.name} ({entry.move.name})" for entry in self.tm_hm],
            "tutor": [entry.name for entry in self.tutor],
            "egg": [entry.name for entry in self.egg],
        }

    @classmethod
    def from_dict(cls, data: dict):
        return SpeciesMoveLearnset(
            level_up=[
                SpeciesLevelUpMove(level=data["level_up"][move_id], move=get_move_by_index(int(move_id)))
                for move_id in data["level_up"]
            ],
            tm_hm=[
                SpeciesTmHmMove(item=get_item_by_move_id(move_id), move=get_move_by_index(move_id))
                for move_id in data["tm_hm"]
            ],
            tutor=[get_move_by_index(move_id) for move_id in data["tutor"]],
            egg=[get_move_by_index(move_id) for move_id in data["egg"]],
        )


@dataclass
class SpeciesEvolution:
    method: str
    method_param: int
    target_species_index: int

    @classmethod
    def from_dict(cls, data: dict) -> "SpeciesEvolution":
        return cls(
            method=data["method"],
            method_param=int(data["method_param"]),
            target_species_index=int(data["target_species"]),
        )


@dataclass
class Species:
    index: int
    national_dex_number: int
    hoenn_dex_number: int
    name: str
    types: list[Type]
    abilities: list[Ability]
    held_items: list[HeldItem]
    base_stats: StatsValues
    gender_ratio: int
    egg_cycles: int
    base_friendship: int
    catch_rate: int
    safari_zone_flee_probability: int
    level_up_type: LevelUpType
    egg_groups: list[str]
    base_experience_yield: int
    ev_yield: StatsValues
    learnset: SpeciesMoveLearnset
    localised_names: dict[str, str]
    evolutions: list[SpeciesEvolution]
    evolves_from: int | None
    family: list[int]

    def has_type(self, type_to_find: Type) -> bool:
        return any(t.index == type_to_find.index for t in self.types)

    def can_learn_tm_hm(self, tm_hm: Item | Move):
        if isinstance(tm_hm, Move):
            tm_hm = tm_hm.tm_hm

        for entry in self.learnset.tm_hm:
            if entry.item == tm_hm:
                return True

        return False

    def to_dict(self) -> dict:
        return _to_dict_helper(self)

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict):
        return Species(
            index=index,
            national_dex_number=data["national_dex_number"],
            hoenn_dex_number=data["hoenn_dex_number"],
            name=data["name"],
            types=list(map(get_type_by_name, data["types"])),
            abilities=list(map(get_ability_by_name, data["abilities"])),
            held_items=list(map(lambda e: HeldItem(e[0], e[1]), data["held_items"])),
            base_stats=StatsValues.from_dict(data["base_stats"]),
            gender_ratio=data["gender_ratio"],
            egg_cycles=data["egg_cycles"],
            base_friendship=data["base_friendship"],
            catch_rate=data["catch_rate"],
            safari_zone_flee_probability=data["safari_zone_flee_probability"],
            level_up_type=LevelUpType(data["level_up_type"]),
            egg_groups=data["egg_groups"],
            base_experience_yield=data["base_experience_yield"],
            ev_yield=StatsValues.from_dict(data["ev_yield"]),
            learnset=SpeciesMoveLearnset.from_dict(data["learnset"]),
            localised_names=data["localised_names"],
            evolutions=[SpeciesEvolution.from_dict(evo_data) for evo_data in data["evolutions"]],
            evolves_from=data["evolves_from"],
            family=data["family"],
        )


@dataclass
class OriginalTrainer:
    id: int
    secret_id: int
    name: str
    gender: Literal["male", "female"]


class Marking(Enum):
    Circle = "●"
    Square = "■"
    Triangle = "▲"
    Heart = "♥"

    def __str__(self):
        return self.value


class StatusCondition(Enum):
    Healthy = "none"
    Sleep = "asleep"
    Poison = "poisoned"
    Burn = "burned"
    Freeze = "frozen"
    Paralysis = "paralysed"
    BadPoison = "badly poisoned"

    @classmethod
    def from_bitfield(cls, bitfield: int):
        if not bitfield:
            return cls.Healthy
        if bitfield & 7:
            return cls.Sleep
        if bitfield & (1 << 3):
            return cls.Poison
        if bitfield & (1 << 4):
            return cls.Burn
        if bitfield & (1 << 5):
            return cls.Freeze
        if bitfield & (1 << 6):
            return cls.Paralysis
        if bitfield & (1 << 7):
            return cls.BadPoison
        return cls.Healthy

    def to_bitfield(self) -> int:
        match self:
            case StatusCondition.Sleep:
                return 1
            case StatusCondition.Poison:
                return 1 << 3
            case StatusCondition.Burn:
                return 1 << 4
            case StatusCondition.Freeze:
                return 1 << 5
            case StatusCondition.Paralysis:
                return 1 << 6
            case StatusCondition.BadPoison:
                return 1 << 7
            case _:
                return 0


@dataclass
class PokerusStatus:
    strain: int
    days_remaining: int


def get_unown_letter_by_index(letter_index: int) -> str:
    if letter_index == 0:
        return "A"
    elif letter_index == 26:
        return "?"
    elif letter_index == 27:
        return "!"
    else:
        return chr(ord("A") + letter_index)


def get_unown_index_by_letter(letter: str) -> int:
    if letter == "?":
        return 26
    elif letter == "!":
        return 27
    else:
        return ord(letter) - ord("A")


def _load_types() -> tuple[dict[str, Type], list[Type]]:
    by_name: dict[str, Type] = {}
    by_index: list[Type] = []
    with open(get_data_path() / "types.json", "r") as file:
        types_data = json.load(file)
        for index in range(len(types_data)):
            name = types_data[index]["name"]
            new_type = Type(index, name)
            by_name[name] = new_type
            by_index.append(new_type)

        for entry in types_data:
            for key in entry["effectiveness"]:
                by_name[entry["name"]].set_effectiveness(by_name[key], entry["effectiveness"][key])
    return by_name, by_index


_types_by_name, _types_by_index = _load_types()


def get_type_by_name(name: str) -> Type:
    return _types_by_name[name]


def get_type_by_index(index: int) -> Type:
    return _types_by_index[index]


def _load_moves() -> tuple[dict[str, Move], list[Move]]:
    by_name: dict[str, Move] = {}
    by_index: list[Move] = []
    with open(get_data_path() / "moves.json", "r") as file:
        moves_data = json.load(file)
        for index in range(len(moves_data)):
            move = Move.from_dict(index, moves_data[index])
            by_name[move.name] = move
            by_index.append(move)
    return by_name, by_index


_moves_by_name, _moves_by_index = _load_moves()


def get_move_by_name(name: str) -> Move:
    return _moves_by_name[name]


def get_move_by_index(index: int) -> Move:
    return _moves_by_index[index]


def _load_natures() -> tuple[dict[str, Nature], list[Nature]]:
    by_name: dict[str, Nature] = {}
    by_index: list[Nature] = []
    with open(get_data_path() / "natures.json", "r") as file:
        natures_data = json.load(file)
        for index in range(len(natures_data)):
            nature = Nature.from_dict(index, natures_data[index])
            by_name[nature.name] = nature
            by_index.append(nature)
    return by_name, by_index


_natures_by_name, _natures_by_index = _load_natures()


def get_nature_by_name(name: str) -> Nature:
    return _natures_by_name[name]


def get_nature_by_index(index: int) -> Nature:
    return _natures_by_index[index]


def _load_abilities() -> tuple[dict[str, Ability], list[Ability]]:
    by_name: dict[str, Ability] = {}
    by_index: list[Ability] = []
    with open(get_data_path() / "abilities.json", "r") as file:
        abilities_data = json.load(file)
        for index in range(len(abilities_data)):
            ability = Ability.from_dict(index, abilities_data[index])
            by_name[ability.name] = ability
            by_index.append(ability)
    return by_name, by_index


_abilities_by_name, _abilities_by_index = _load_abilities()


def get_ability_by_name(name: str) -> Ability:
    return _abilities_by_name[name]


def get_ability_by_index(index: int) -> Ability:
    return _abilities_by_index[index]


def _load_species() -> tuple[dict[str, Species], list[Species], dict[int, Species]]:
    by_name: dict[str, Species] = {}
    by_index: list[Species] = []
    by_national_dex: dict[int, Species] = {}
    with open(get_data_path() / "species.json", "r") as file:
        species_data = json.load(file)
        for index in range(len(species_data)):
            species = Species.from_dict(index, species_data[index])
            by_name[species.name] = species
            by_index.append(species)
            by_national_dex[species.national_dex_number] = species
    return by_name, by_index, by_national_dex


_species_by_name, _species_by_index, _species_by_national_dex = _load_species()


def get_species_by_name(name: str) -> Species:
    if name.startswith("Unown ("):
        name = "Unown"

    return _species_by_name[name]


def get_species_by_index(index: int) -> Species:
    # We use species IDs 20100+ for differentiating between Unown forms, so any
    # such ID should be mapped back to the Unown species.
    if index >= 20100 and index < 20200:
        index = 201

    return _species_by_index[index]


def get_species_by_national_dex(national_dex_number: int) -> Species:
    return _species_by_national_dex[national_dex_number]


def _to_dict_helper(value) -> any:
    if value is None:
        return value

    debug_dict_callback = getattr(value, "debug_dict_value", None)
    if callable(debug_dict_callback):
        return _to_dict_helper(debug_dict_callback())

    if type(value) is dict:
        return {k: _to_dict_helper(value[k]) for k in value}
    if isinstance(value, (list, set, tuple, frozenset)):
        return [_to_dict_helper(v) for v in value]
    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Enum):
        return value.name

    result = {}
    with contextlib.suppress(AttributeError):
        for k in value.__dict__:
            if not k.startswith("_") and k != "data":
                result[k] = _to_dict_helper(value.__dict__[k])
    if hasattr(value, "__class__"):
        for k in dir(value.__class__):
            if not k.startswith("_") and isinstance(getattr(value.__class__, k), property):
                result[k] = _to_dict_helper(getattr(value, k))

    return result
