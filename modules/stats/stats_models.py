# Copyright (c) 2026 realgarit
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from typing import TYPE_CHECKING, Optional

from modules.battle.battle_state import BattleOutcome, EncounterType
from modules.items.items import Item
from modules.pokemon.pokemon import Pokemon, Species, get_species_by_index, get_unown_letter_by_index, get_unown_index_by_letter
from modules.items.fishing import FishingAttempt, FishingResult

if TYPE_CHECKING:
    from modules.pokemon.encounter import EncounterInfo


class StatsDatabaseSchemaTooNew(Exception):
    pass


class BaseData:
    key: str
    value: str | None


@dataclass
class SpeciesRecord:
    value: int
    species: "Species"
    species_form: str | None = None

    @classmethod
    def from_row_values(cls, value, species_id) -> "SpeciesRecord | None":
        if not species_id:
            return None
        elif species_id >= 20100 and species_id < 20200:
            return cls(value, get_species_by_index(201), get_unown_letter_by_index(species_id - 20100))
        else:
            return cls(value, get_species_by_index(species_id))

    @classmethod
    def create(cls, value, pokemon: "Pokemon") -> "SpeciesRecord":
        if pokemon.species.name == "Unown":
            return cls(value, pokemon.species, pokemon.unown_letter)
        else:
            return cls(value, pokemon.species)

    def __int__(self):
        return self.value

    def __eq__(self, value):
        return self.value == value if isinstance(value, (int, float)) else NotImplemented

    def __ne__(self, value):
        return self.value != value if isinstance(value, (int, float)) else NotImplemented

    def __gt__(self, value):
        return self.value > value if isinstance(value, (int, float)) else NotImplemented

    def __ge__(self, value):
        return self.value >= value if isinstance(value, (int, float)) else NotImplemented

    def __lt__(self, value):
        return self.value < value if isinstance(value, (int, float)) else NotImplemented

    def __le__(self, value):
        return self.value <= value if isinstance(value, (int, float)) else NotImplemented

    def __iadd__(self, value):
        if isinstance(value, int):
            self.value += value
            return self
        else:
            return NotImplemented

    def is_same_species(self, pokemon: "Pokemon") -> bool:
        return pokemon.species.index == self.species.index and (
            pokemon.species.name != "Unown" or pokemon.unown_letter == self.species_form
        )

    def copy(self) -> "SpeciesRecord":
        return SpeciesRecord(self.value, self.species, self.species_form)

    @property
    def species_id_for_database(self) -> int:
        if self.species.name == "Unown" and self.species_form is not None:
            return 20100 + get_unown_index_by_letter(self.species_form)
        else:
            return self.species.index

    @property
    def species_name(self) -> str:
        if self.species.name == "Unown" and self.species_form is not None:
            return f"{self.species.name} ({self.species_form})"
        else:
            return self.species.name

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "species_name": self.species_name,
        }


@dataclass
class Encounter:
    encounter_id: int
    shiny_phase_id: int
    matching_custom_catch_filters: str | None
    encounter_time: datetime
    map: str | None
    coordinates: str | None
    bot_mode: str
    type: EncounterType | None
    outcome: BattleOutcome | None
    pokemon: "Pokemon"

    @classmethod
    def from_row_data(cls, row: list | tuple) -> "Encounter":
        return Encounter(
            encounter_id=row[0],
            shiny_phase_id=row[3],
            matching_custom_catch_filters=row[6],
            encounter_time=datetime.fromisoformat(row[7]),
            map=row[8],
            coordinates=row[9],
            bot_mode=row[10],
            type=EncounterType(row[11]) if row[11] else None,
            outcome=BattleOutcome(row[12]) if row[12] else None,
            pokemon=Pokemon(row[13]),
        )

    @property
    def species_id(self) -> int:
        return self.pokemon.species.index

    @property
    def species_name(self) -> str:
        return self.pokemon.species_name_for_stats

    @property
    def is_shiny(self) -> bool:
        return self.pokemon.is_shiny

    @property
    def iv_sum(self) -> int:
        return self.pokemon.ivs.sum()

    @property
    def shiny_value(self) -> int:
        return self.pokemon.shiny_value

    @property
    def data(self) -> bytes:
        return self.pokemon.data

    def to_dict(self) -> dict:
        return {
            "encounter_id": self.encounter_id,
            "shiny_phase_id": self.shiny_phase_id,
            "matching_custom_catch_filters": self.matching_custom_catch_filters,
            "encounter_time": self.encounter_time.isoformat(),
            "map": self.map,
            "coordinates": self.coordinates,
            "bot_mode": self.bot_mode,
            "type": self.type.value if self.type else None,
            "outcome": self.outcome.name if self.outcome is not None else None,
            "pokemon": self.pokemon.to_dict(),
        }


@dataclass
class EncounterSummary:
    species: "Species"
    species_form: str | None
    total_encounters: int
    shiny_encounters: int
    catches: int
    total_highest_iv_sum: int
    total_lowest_iv_sum: int
    total_highest_sv: int
    total_lowest_sv: int
    phase_encounters: int
    phase_highest_iv_sum: int | None
    phase_lowest_iv_sum: int | None
    phase_highest_sv: int | None
    phase_lowest_sv: int | None
    last_encounter_time: datetime

    @classmethod
    def create(cls, encounter: Encounter) -> "EncounterSummary":
        return cls(
            species=encounter.pokemon.species,
            species_form=encounter.pokemon.unown_letter if encounter.pokemon.species.name == "Unown" else None,
            total_encounters=1,
            shiny_encounters=0 if not encounter.is_shiny else 1,
            catches=0,
            total_highest_iv_sum=encounter.iv_sum,
            total_lowest_iv_sum=encounter.iv_sum,
            total_highest_sv=encounter.shiny_value,
            total_lowest_sv=encounter.shiny_value,
            phase_encounters=1 if not encounter.is_shiny else 0,
            phase_highest_iv_sum=encounter.iv_sum if not encounter.is_shiny else None,
            phase_lowest_iv_sum=encounter.iv_sum if not encounter.is_shiny else None,
            phase_highest_sv=encounter.shiny_value if not encounter.is_shiny else None,
            phase_lowest_sv=encounter.shiny_value if not encounter.is_shiny else None,
            last_encounter_time=encounter.encounter_time,
        )

    def update(self, encounter: Encounter):
        self.total_encounters += 1
        self.last_encounter_time = encounter.encounter_time

        if self.total_highest_iv_sum < encounter.iv_sum:
            self.total_highest_iv_sum = encounter.iv_sum

        if self.total_lowest_iv_sum > encounter.iv_sum:
            self.total_lowest_iv_sum = encounter.iv_sum

        if self.total_highest_sv < encounter.shiny_value:
            self.total_highest_sv = encounter.shiny_value

        if self.total_lowest_sv > encounter.shiny_value:
            self.total_lowest_sv = encounter.shiny_value

        self.phase_encounters += 1

        if self.phase_highest_iv_sum is None or self.phase_highest_iv_sum < encounter.iv_sum:
            self.phase_highest_iv_sum = encounter.iv_sum

        if self.phase_lowest_iv_sum is None or self.phase_lowest_iv_sum > encounter.iv_sum:
            self.phase_lowest_iv_sum = encounter.iv_sum

        if not encounter.is_shiny:
            if self.phase_highest_sv is None or self.phase_highest_sv < encounter.shiny_value:
                self.phase_highest_sv = encounter.shiny_value

            if self.phase_lowest_sv is None or self.phase_lowest_sv > encounter.shiny_value:
                self.phase_lowest_sv = encounter.shiny_value
        else:
            self.shiny_encounters += 1

    def update_outcome(self, outcome: BattleOutcome) -> None:
        if outcome is BattleOutcome.Caught:
            self.catches += 1

    def is_same_species(self, pokemon: "Pokemon") -> bool:
        return pokemon.species.index == self.species.index and (
            pokemon.species.name != "Unown" or pokemon.unown_letter == self.species_form
        )

    @property
    def species_id_for_database(self) -> int:
        if self.species.name == "Unown" and self.species_form is not None:
            return 20100 + get_unown_index_by_letter(self.species_form)
        else:
            return self.species.index

    @property
    def species_name(self) -> str:
        if self.species.name == "Unown" and self.species_form is not None:
            return f"{self.species.name} ({self.species_form})"
        else:
            return self.species.name

    def to_dict(self) -> dict:
        return {
            "species_id": self.species.index,
            "species_name": self.species_name,
            "total_encounters": self.total_encounters,
            "shiny_encounters": self.shiny_encounters,
            "catches": self.catches,
            "total_highest_iv_sum": self.total_highest_iv_sum,
            "total_lowest_iv_sum": self.total_lowest_iv_sum,
            "total_highest_sv": self.total_highest_sv,
            "total_lowest_sv": self.total_lowest_sv,
            "phase_encounters": self.phase_encounters,
            "phase_highest_iv_sum": self.phase_highest_iv_sum,
            "phase_lowest_iv_sum": self.phase_lowest_iv_sum,
            "phase_highest_sv": self.phase_highest_sv,
            "phase_lowest_sv": self.phase_lowest_sv,
            "last_encounter_time": self.last_encounter_time.isoformat(),
        }


@dataclass
class ShinyPhase:
    shiny_phase_id: int
    start_time: datetime
    end_time: datetime | None = None
    shiny_encounter: Encounter | None = None
    encounters: int = 0
    highest_iv_sum: SpeciesRecord | None = None
    lowest_iv_sum: SpeciesRecord | None = None
    highest_sv: SpeciesRecord | None = None
    lowest_sv: SpeciesRecord | None = None
    longest_streak: SpeciesRecord | None = None
    current_streak: SpeciesRecord | None = None
    fishing_attempts: int = 0
    successful_fishing_attempts: int = 0
    longest_unsuccessful_fishing_streak: int = 0
    current_unsuccessful_fishing_streak: int = 0
    pokenav_calls: int = 0

    snapshot_total_encounters: int | None = None
    snapshot_total_shiny_encounters: int | None = None
    snapshot_species_encounters: int | None = None
    snapshot_species_shiny_encounters: int | None = None

    @classmethod
    def from_row_data(cls, row: list | tuple, shiny_encounter: Encounter | None) -> "ShinyPhase":
        return ShinyPhase(
            row[0],
            datetime.fromisoformat(row[1]),
            datetime.fromisoformat(row[2]) if row[2] is not None else None,
            shiny_encounter,
            row[4],
            SpeciesRecord.from_row_values(row[5], row[6]),
            SpeciesRecord.from_row_values(row[7], row[8]),
            SpeciesRecord.from_row_values(row[9], row[10]),
            SpeciesRecord.from_row_values(row[11], row[12]),
            SpeciesRecord.from_row_values(row[13], row[14]),
            SpeciesRecord.from_row_values(row[15], row[16]),
            row[17],
            row[18],
            row[19],
            row[20],
            row[21],
            row[22],
            row[23],
            row[24],
            row[25],
        )

    @classmethod
    def create(cls, shiny_phase_id: int, start_time: datetime) -> "ShinyPhase":
        return cls(shiny_phase_id=shiny_phase_id, start_time=start_time)

    def update(self, encounter: Encounter):
        self.encounters += 1

        if self.highest_iv_sum is None or self.highest_iv_sum < encounter.iv_sum:
            self.highest_iv_sum = SpeciesRecord.create(encounter.iv_sum, encounter.pokemon)

        if self.lowest_iv_sum is None or self.lowest_iv_sum > encounter.iv_sum:
            self.lowest_iv_sum = SpeciesRecord.create(encounter.iv_sum, encounter.pokemon)

        if not encounter.is_shiny:
            if self.highest_sv is None or self.highest_sv < encounter.shiny_value:
                self.highest_sv = SpeciesRecord.create(encounter.shiny_value, encounter.pokemon)

            if self.lowest_sv is None or self.lowest_sv > encounter.shiny_value:
                self.lowest_sv = SpeciesRecord.create(encounter.shiny_value, encounter.pokemon)

        if self.current_streak is None or not self.current_streak.is_same_species(encounter.pokemon):
            self.current_streak = SpeciesRecord.create(1, encounter.pokemon)
        else:
            self.current_streak += 1

        if self.longest_streak is None or self.current_streak.value > self.longest_streak.value:
            self.longest_streak = self.current_streak.copy()

    def update_fishing_attempt(self, attempt: FishingAttempt):
        self.fishing_attempts += 1
        if attempt.result is not FishingResult.Encounter:
            self.current_unsuccessful_fishing_streak += 1
            if self.current_unsuccessful_fishing_streak > self.longest_unsuccessful_fishing_streak:
                self.longest_unsuccessful_fishing_streak = self.current_unsuccessful_fishing_streak
        else:
            self.successful_fishing_attempts += 1
            self.current_unsuccessful_fishing_streak = 0

    def update_snapshot(self, encounter_summaries: dict[int, "EncounterSummary"]):
        self.snapshot_total_encounters = 0
        self.snapshot_total_shiny_encounters = 0
        for species_id in encounter_summaries:
            encounter_summary = encounter_summaries[species_id]
            self.snapshot_total_encounters += encounter_summary.total_encounters
            self.snapshot_total_shiny_encounters += encounter_summary.shiny_encounters
            if encounter_summaries[species_id].is_same_species(self.shiny_encounter.pokemon):
                self.snapshot_species_encounters = encounter_summary.total_encounters
                self.snapshot_species_shiny_encounters = encounter_summary.shiny_encounters

    def to_dict(self) -> dict:
        return {
            "phase": {
                "shiny_phase_id": self.shiny_phase_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time is not None else None,
                "encounters": self.encounters,
                "highest_iv_sum": self.highest_iv_sum.to_dict() if self.highest_iv_sum is not None else None,
                "lowest_iv_sum": self.lowest_iv_sum.to_dict() if self.lowest_iv_sum is not None else None,
                "highest_sv": self.highest_sv.to_dict() if self.highest_sv is not None else None,
                "lowest_sv": self.lowest_sv.to_dict() if self.lowest_sv is not None else None,
                "longest_streak": self.longest_streak.to_dict() if self.longest_streak is not None else None,
                "current_streak": self.current_streak.to_dict() if self.current_streak is not None else None,
                "fishing_attempts": self.fishing_attempts,
                "successful_fishing_attempts": self.successful_fishing_attempts,
                "longest_unsuccessful_fishing_streak": self.longest_unsuccessful_fishing_streak,
                "current_unsuccessful_fishing_streak": self.current_unsuccessful_fishing_streak,
                "pokenav_calls": self.pokenav_calls,
            },
            "snapshot": {
                "total_encounters": self.snapshot_total_encounters,
                "total_shiny_encounters": self.snapshot_total_shiny_encounters,
                "species_encounters": self.snapshot_species_encounters,
                "species_shiny_encounters": self.snapshot_species_shiny_encounters,
            },
            "shiny_encounter": self.shiny_encounter.to_dict() if self.shiny_encounter is not None else None,
        }


@dataclass
class EncounterTotals:
    total_encounters: int = 0
    shiny_encounters: int = 0
    catches: int = 0
    total_highest_iv_sum: SpeciesRecord | None = None
    total_lowest_iv_sum: SpeciesRecord | None = None
    total_highest_sv: SpeciesRecord | None = None
    total_lowest_sv: SpeciesRecord | None = None
    phase_encounters: int = 0
    phase_highest_iv_sum: SpeciesRecord | None = None
    phase_lowest_iv_sum: SpeciesRecord | None = None
    phase_highest_sv: SpeciesRecord | None = None
    phase_lowest_sv: SpeciesRecord | None = None

    @classmethod
    def from_summaries(cls, encounter_summaries: dict[int, "EncounterSummary"]) -> "EncounterTotals":
        totals = cls()
        for species_id in encounter_summaries:
            encounter_summary = encounter_summaries[species_id]

            totals.total_encounters += encounter_summary.total_encounters
            totals.shiny_encounters += encounter_summary.shiny_encounters
            totals.catches += encounter_summary.catches
            totals.phase_encounters += encounter_summary.phase_encounters

            values_to_total = [
                ("total_highest_iv_sum", max),
                ("total_lowest_iv_sum", min),
                ("total_highest_sv", max),
                ("total_lowest_sv", min),
                ("phase_highest_iv_sum", max),
                ("phase_lowest_iv_sum", min),
                ("phase_highest_sv", max),
                ("phase_lowest_sv", min),
            ]
            for property_name, comparison in values_to_total:
                total_value = getattr(totals, property_name)
                summary_value = getattr(encounter_summary, property_name)
                if (total_value is None and summary_value is not None) or (
                    total_value is not None
                    and summary_value is not None
                    and comparison(total_value, summary_value) != total_value
                ):
                    setattr(
                        totals,
                        property_name,
                        SpeciesRecord(summary_value, encounter_summary.species, encounter_summary.species_form),
                    )

        return totals

    def to_dict(self) -> dict:
        return {
            "total_encounters": self.total_encounters,
            "shiny_encounters": self.shiny_encounters,
            "catches": self.catches,
            "total_highest_iv_sum": self.total_highest_iv_sum.to_dict() if self.total_highest_iv_sum else None,
            "total_lowest_iv_sum": self.total_lowest_iv_sum.to_dict() if self.total_lowest_iv_sum else None,
            "total_highest_sv": self.total_highest_sv.to_dict() if self.total_highest_sv else None,
            "total_lowest_sv": self.total_lowest_sv.to_dict() if self.total_lowest_sv else None,
            "phase_encounters": self.phase_encounters,
            "phase_highest_iv_sum": self.phase_highest_iv_sum.to_dict() if self.phase_highest_iv_sum else None,
            "phase_lowest_iv_sum": self.phase_lowest_iv_sum.to_dict() if self.phase_lowest_iv_sum else None,
            "phase_highest_sv": self.phase_highest_sv.to_dict() if self.phase_highest_sv else None,
            "phase_lowest_sv": self.phase_lowest_sv.to_dict() if self.phase_lowest_sv else None,
        }


@dataclass
class PickupItem:
    item: "Item"
    times_picked_up: int = 0


@dataclass
class GlobalStats:
    encounter_summaries: dict[int, EncounterSummary]
    pickup_items: dict[int, PickupItem]
    current_shiny_phase: ShinyPhase | None
    longest_shiny_phase: ShinyPhase | None
    shortest_shiny_phase: ShinyPhase | None

    @cached_property
    def totals(self) -> EncounterTotals:
        return EncounterTotals.from_summaries(self.encounter_summaries)

    def species(self, pokemon: Pokemon) -> EncounterSummary:
        if pokemon.species.name == "Unown":
            species_index = 20100 + get_unown_index_by_letter(pokemon.unown_letter)
        else:
            species_index = pokemon.species.index

        if species_index in self.encounter_summaries:
            return self.encounter_summaries[species_index]
        else:
            return EncounterSummary(
                species=pokemon.species,
                species_form=pokemon.unown_letter if pokemon.species.name == "Unown" else None,
                total_encounters=0,
                shiny_encounters=0,
                catches=0,
                total_highest_iv_sum=0,
                total_lowest_iv_sum=0,
                total_highest_sv=0,
                total_lowest_sv=0,
                phase_encounters=0,
                phase_highest_iv_sum=0,
                phase_lowest_iv_sum=0,
                phase_highest_sv=0,
                phase_lowest_sv=0,
                last_encounter_time=datetime.now(timezone.utc),
            )

    def to_dict(self):
        phase = (
            ShinyPhase(0, datetime.now(timezone.utc)) if self.current_shiny_phase is None else self.current_shiny_phase
        )

        longest_shiny_phase = phase if self.longest_shiny_phase is None else self.longest_shiny_phase
        shortest_shiny_phase = phase if self.shortest_shiny_phase is None else self.shortest_shiny_phase

        return {
            "pokemon": {summary.species_name: summary.to_dict() for summary in self.encounter_summaries.values()},
            "totals": self.totals.to_dict(),
            "current_phase": {
                "start_time": phase.start_time.isoformat(),
                "encounters": phase.encounters,
                "highest_iv_sum": phase.highest_iv_sum.to_dict() if phase.highest_iv_sum is not None else None,
                "lowest_iv_sum": phase.lowest_iv_sum.to_dict() if phase.lowest_iv_sum is not None else None,
                "highest_sv": phase.highest_sv.to_dict() if phase.highest_sv is not None else None,
                "lowest_sv": phase.lowest_sv.to_dict() if phase.lowest_sv is not None else None,
                "longest_streak": phase.longest_streak.to_dict() if phase.longest_streak is not None else None,
                "current_streak": phase.current_streak.to_dict() if phase.current_streak is not None else None,
                "fishing_attempts": phase.fishing_attempts,
                "successful_fishing_attempts": phase.successful_fishing_attempts,
                "longest_unsuccessful_fishing_streak": phase.longest_unsuccessful_fishing_streak,
                "current_unsuccessful_fishing_streak": phase.current_unsuccessful_fishing_streak,
                "pokenav_calls": phase.pokenav_calls,
            },
            "longest_phase": {
                "value": longest_shiny_phase.encounters,
                "species_name": (
                    longest_shiny_phase.shiny_encounter.species_name
                    if longest_shiny_phase.shiny_encounter is not None
                    else None
                ),
            },
            "shortest_phase": {
                "value": shortest_shiny_phase.encounters,
                "species_name": (
                    shortest_shiny_phase.shiny_encounter.species_name
                    if shortest_shiny_phase.shiny_encounter is not None
                    else None
                ),
            },
            "pickup_items": {entry.item.name: entry.times_picked_up for entry in self.pickup_items.values()},
        }
