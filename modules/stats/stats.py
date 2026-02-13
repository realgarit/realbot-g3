# Copyright (c) 2026 realgarit
import os
import sqlite3
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from textwrap import dedent
from typing import TYPE_CHECKING, Iterable, Optional

from modules.battle.battle_state import BattleOutcome
from modules.core.console import console
from modules.core.context import context
from modules.items.fishing import FishingAttempt, FishingResult
from modules.items.items import Item, get_item_by_index
from modules.pokemon.pokemon import Pokemon, get_species_by_index, get_unown_letter_by_index, get_unown_index_by_letter

if TYPE_CHECKING:
    from modules.pokemon.encounter import EncounterInfo
    from modules.core.profiles import Profile


from modules.stats.stats_models import (
    Encounter,
    EncounterSummary,
    GlobalStats,
    PickupItem,
    ShinyPhase,
    StatsDatabaseSchemaTooNew,
)

current_schema_version = 3




class StatsDatabase:
    def __init__(self, profile: "Profile"):
        self.encounter_rate: int = 0
        self.encounter_rate_at_1x: float = 0.0

        self._connection = sqlite3.connect(profile.path / "stats.db", check_same_thread=False)
        self._cursor = self._connection.cursor()
        self._lock = threading.Lock()

        db_schema_version = self._get_schema_version()
        if db_schema_version < current_schema_version:
            self._update_schema(db_schema_version)
            if db_schema_version == 0 and (profile.path / "stats").is_dir():
                self._migrate_old_stats(profile)
        elif db_schema_version > current_schema_version:
            raise StatsDatabaseSchemaTooNew(
                f"The profile's stats database schema has version {db_schema_version}, but this version of the bot only supports version {current_schema_version}. Cannot load stats."
            )

        self.last_encounter: Encounter | None = self._get_last_encounter()
        self.last_fishing_attempt: Optional[FishingAttempt] = None
        self.last_shiny_species_phase_encounters: int | None = None

        self.current_shiny_phase: ShinyPhase | None = self._get_current_shiny_phase()
        self._shortest_shiny_phase: ShinyPhase | None = self._get_shortest_shiny_phase()
        self._longest_shiny_phase: ShinyPhase | None = self._get_longest_shiny_phase()
        self._next_encounter_id: int = self._get_next_encounter_id()
        self._encounter_summaries: dict[int, EncounterSummary] = self._get_encounter_summaries()
        self._pickup_items: dict[int, PickupItem] = self._get_pickup_items()
        self._base_data: dict[str, str | None] = self._get_base_data()

        # Normally, the encounter rate is calculated based on the previous 100 encounters. Which
        # is accurate enough to get a rough idea of how fast things are going, and it means that
        # a long break in between encounters (due to changing modes, playing manually etc.) will
        # be flushed out reasonably soon.
        # But when trying to measure a more accurate encounters/hr for a given route, we need a
        # larger sample size because the encounter rate can fluctuate quite a bit in some modes.
        #
        # So rather than constantly having to edit this file, this allows setting the environment
        # variable `REALBOT_ENCOUNTER_BENCHMARK` to anything but an empty string in order to
        # increase the sample size to 1,000.
        encounter_buffer_size = 1000 if os.getenv("REALBOT_ENCOUNTER_BENCHMARK", "") != "" else 100
        self._encounter_timestamps: deque[float] = deque(maxlen=encounter_buffer_size)
        self._encounter_frames: deque[int] = deque(maxlen=encounter_buffer_size)

    def set_data(self, key: str, value: str | None):
        self._execute_write("REPLACE INTO base_data (data_key, value) VALUES (?, ?)", (key, value))
        self._base_data[key] = value
        self._commit()

    def get_data(self, key: str) -> str | None:
        return self._base_data[key] if key in self._base_data else None

    def log_encounter(self, encounter_info: "EncounterInfo") -> Encounter:
        encounter_time_in_utc = encounter_info.encounter_time.replace(tzinfo=timezone.utc)

        self._update_encounter_rates()

        if self.current_shiny_phase is None:
            shiny_phase_id = self._get_next_shiny_phase_id()
            self.current_shiny_phase = ShinyPhase.create(shiny_phase_id, encounter_time_in_utc)
            self._insert_shiny_phase(self.current_shiny_phase)

        encounter = Encounter(
            encounter_id=self._next_encounter_id,
            shiny_phase_id=self.current_shiny_phase.shiny_phase_id,
            matching_custom_catch_filters=encounter_info.catch_filters_result,
            encounter_time=encounter_time_in_utc,
            map=encounter_info.map.name,
            coordinates=f"{encounter_info.coordinates[0]}:{encounter_info.coordinates[1]}",
            bot_mode=encounter_info.bot_mode,
            type=encounter_info.type,
            outcome=None,
            pokemon=encounter_info.pokemon,
        )

        self.last_encounter = encounter
        if context.config.logging.log_encounters or encounter_info.is_of_interest:
            self._insert_encounter(encounter)
        self.current_shiny_phase.update(encounter)
        self._update_shiny_phase(self.current_shiny_phase)

        if encounter.pokemon.species.name == "Unown":
            species_index = 20100 + get_unown_index_by_letter(encounter.pokemon.unown_letter)
        else:
            species_index = encounter.pokemon.species.index

        if species_index not in self._encounter_summaries:
            self._encounter_summaries[species_index] = EncounterSummary.create(encounter)
        else:
            self._encounter_summaries[species_index].update(encounter)

        self._insert_or_update_encounter_summary(self._encounter_summaries[species_index])
        self._commit()
        self._next_encounter_id += 1

        if encounter_info.battle_outcome is not None:
            self.log_end_of_battle(encounter_info.battle_outcome, encounter_info)

        return encounter

    def clear_current_shiny_phase(self):
        """
        This will clear all the stats for the current shiny phase WITHOUT marking it
        as completed. This can be used to make it start again from a clean 0 encounters
        in case there have been some bogus encounters from walking around or something
        like that.

        It will not affect total numbers.
        """

        if self.current_shiny_phase is None:
            return

        self.current_shiny_phase.start_time = datetime.now(timezone.utc)
        self.current_shiny_phase.shiny_encounter = 0
        self.current_shiny_phase.encounters = 0
        self.current_shiny_phase.highest_iv_sum = None
        self.current_shiny_phase.lowest_iv_sum = None
        self.current_shiny_phase.highest_sv = None
        self.current_shiny_phase.lowest_sv = None
        self.current_shiny_phase.longest_streak = None
        self.current_shiny_phase.current_streak = None
        self.current_shiny_phase.fishing_attempts = 0
        self.current_shiny_phase.successful_fishing_attempts = 0
        self.current_shiny_phase.longest_unsuccessful_fishing_streak = 0
        self.current_shiny_phase.current_unsuccessful_fishing_streak = 0
        self.current_shiny_phase.pokenav_calls = 0
        self._update_shiny_phase(self.current_shiny_phase)

        self._execute_write(
            """
            UPDATE shiny_phases
            SET start_time = ?
            WHERE shiny_phase_id = ?
            """,
            (self.current_shiny_phase.start_time, self.current_shiny_phase.shiny_phase_id),
        )

        self._execute_write(
            """
            UPDATE encounter_summaries
            SET phase_encounters = 0,
                phase_highest_iv_sum = NULL,
                phase_lowest_iv_sum = NULL,
                phase_highest_sv = NULL,
                phase_lowest_sv = NULL
            """
        )

        for index in self._encounter_summaries:
            summary = self._encounter_summaries[index]
            summary.phase_encounters = 0
            summary.phase_highest_iv_sum = None
            summary.phase_lowest_iv_sum = None
            summary.phase_highest_sv = None
            summary.phase_lowest_sv = None

        self._commit()

    def reset_shiny_phase(self, encounter: Encounter):
        """
        Marks the current shiny phase as completed and starts a new one.

        :param encounter: Shiny encounter that ended the phase
        """
        self.current_shiny_phase.shiny_encounter = encounter
        self.current_shiny_phase.end_time = encounter.encounter_time
        self.current_shiny_phase.update_snapshot(self._encounter_summaries)
        self._update_shiny_phase(self.current_shiny_phase)
        self._reset_phase_in_database(encounter)
        if (
            self._shortest_shiny_phase is None
            or self.current_shiny_phase.encounters < self._shortest_shiny_phase.encounters
        ):
            self._shortest_shiny_phase = self.current_shiny_phase
        if (
            self._longest_shiny_phase is None
            or self.current_shiny_phase.encounters > self._longest_shiny_phase.encounters
        ):
            self._longest_shiny_phase = self.current_shiny_phase
        self.current_shiny_phase = None
        for species_id in self._encounter_summaries:
            if self._encounter_summaries[species_id].is_same_species(encounter.pokemon):
                self.last_shiny_species_phase_encounters = self._encounter_summaries[species_id].phase_encounters

            encounter_summary = self._encounter_summaries[species_id]
            encounter_summary.phase_encounters = 0
            encounter_summary.phase_highest_iv_sum = None
            encounter_summary.phase_lowest_iv_sum = None
            encounter_summary.phase_highest_sv = None
            encounter_summary.phase_lowest_sv = None

        self._commit()

    def log_end_of_battle(self, battle_outcome: "BattleOutcome", encounter_info: "EncounterInfo"):
        if self.last_encounter is not None:
            self.last_encounter.outcome = battle_outcome
            self._update_encounter_outcome(self.last_encounter)
            if self.last_encounter.species_id in self._encounter_summaries and encounter_info.is_of_interest:
                self._encounter_summaries[self.last_encounter.species_id].update_outcome(battle_outcome)
                self._insert_or_update_encounter_summary(self._encounter_summaries[self.last_encounter.species_id])
            self._commit()

    def log_pickup_items(self, picked_up_items: list["Item"]) -> None:
        need_updating: set[int] = set()
        for item in picked_up_items:
            if item.index not in self._pickup_items:
                self._pickup_items[item.index] = PickupItem(item)
            self._pickup_items[item.index].times_picked_up += 1
            need_updating.add(item.index)
        for item_index in need_updating:
            self._insert_or_update_pickup_item(self._pickup_items[item_index])
            self._commit()

    def log_fishing_attempt(self, attempt: FishingAttempt):
        self.last_fishing_attempt = attempt
        if self.current_shiny_phase is not None:
            self.current_shiny_phase.update_fishing_attempt(attempt)
            if attempt.result is not FishingResult.Encounter:
                self._update_shiny_phase(self.current_shiny_phase)
                self._commit()
        context.message = f"Fishing attempt with {attempt.rod.name} and result {attempt.result.name}"

    def log_pokenav_call(self):
        if self.current_shiny_phase is not None:
            self.current_shiny_phase.pokenav_calls += 1
            self._update_shiny_phase(self.current_shiny_phase)
            self._commit()

    def get_global_stats(self) -> GlobalStats:
        return GlobalStats(
            self._encounter_summaries,
            self._pickup_items,
            self.current_shiny_phase,
            self._longest_shiny_phase,
            self._shortest_shiny_phase,
        )

    def get_encounter_log(self) -> list[Encounter]:
        return list(self.query_encounters())

    def get_shiny_phase_by_shiny(self, shiny_pokemon: Pokemon) -> ShinyPhase | None:
        return self._query_single_shiny_phase("encounters.personality_value = ?", (shiny_pokemon.personality_value,))

    def get_shiny_log(self) -> list[ShinyPhase]:
        return list(self._query_shiny_phases("end_time IS NOT NULL ORDER BY end_time DESC"))

    def has_encounter_with_personality_value(self, personality_value: int) -> bool:
        return self.count_encounters("personality_value = ?", [personality_value]) > 0

    def query_encounters(
        self,
        where_clause: str | None = None,
        parameters: tuple | list | None = None,
        limit: int | None = 10,
        offset: int = 0,
    ) -> Iterable[Encounter]:
        result = self._cursor.execute(
            f"""
            SELECT
                encounter_id,
                species_id,
                personality_value,
                shiny_phase_id,
                is_shiny,
                is_roamer,
                matching_custom_catch_filters,
                encounter_time,
                map,
                coordinates,
                bot_mode,
                type,
                outcome,
                data
            FROM encounters
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            ORDER BY encounter_id DESC
            {f'LIMIT {limit} OFFSET {offset}' if limit is not None else ''}
            """,
            [] if parameters is None else parameters,
        )
        for row in result:
            yield Encounter.from_row_data(row)

    def count_encounters(self, where_clause: str | None = None, parameters: tuple | list | None = None) -> int:
        result = self._cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM encounters
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            """,
            [] if parameters is None else parameters,
        )

        return int(result.fetchone()[0])

    def _update_encounter_rates(self) -> None:
        self._encounter_timestamps.append(time.time())
        self._encounter_frames.append(context.frame)

        number_of_encounters = len(self._encounter_timestamps)
        if number_of_encounters > 1:
            first_recorded_timestamp = self._encounter_timestamps[0]
            last_recorded_timestamp = self._encounter_timestamps[-1]
            timestamp_diff = last_recorded_timestamp - first_recorded_timestamp
            average_time_per_encounter = timestamp_diff / (number_of_encounters - 1)
            if average_time_per_encounter > 0:
                self.encounter_rate = int(3600 / average_time_per_encounter)
            else:
                self.encounter_rate = 0

        number_of_encounters = len(self._encounter_frames)
        if number_of_encounters > 1:
            first_recorded_frame = self._encounter_frames[0]
            last_recorded_frame = self._encounter_frames[-1]
            frame_diff = last_recorded_frame - first_recorded_frame
            average_frames_per_encounter = frame_diff / (number_of_encounters - 1)
            average_seconds_per_encounter = average_frames_per_encounter / 59.727500569606
            if average_seconds_per_encounter > 0:
                self.encounter_rate_at_1x = round(3600 / average_seconds_per_encounter, 1)
            else:
                self.encounter_rate_at_1x = 0

    def _get_next_encounter_id(self) -> int:
        result = self._cursor.execute(
            "SELECT encounter_id FROM encounters ORDER BY encounter_id DESC LIMIT 1"
        ).fetchone()
        if result is None:
            return 1
        else:
            return int(result[0]) + 1

    def _get_current_shiny_phase(self) -> ShinyPhase | None:
        return self._query_single_shiny_phase("end_time IS NULL ORDER BY shiny_phases.shiny_phase_id DESC")

    def _get_shiny_phase_by_id(self, shiny_phase_id: int) -> ShinyPhase | None:
        return self._query_single_shiny_phase("shiny_phases.shiny_phase_id = ?", (shiny_phase_id,))

    def _get_shortest_shiny_phase(self) -> ShinyPhase | None:
        return self._query_single_shiny_phase("end_time IS NOT NULL ORDER BY encounters ASC")

    def _get_longest_shiny_phase(self) -> ShinyPhase | None:
        return self._query_single_shiny_phase("end_time IS NOT NULL ORDER BY encounters DESC")

    def _query_shiny_phases(
        self, where_clause: str, parameters: tuple | list | None = None, limit: int | None = 10, offset: int = 0
    ) -> Iterable[ShinyPhase]:
        result = self._cursor.execute(
            f"""
            SELECT
                shiny_phases.shiny_phase_id,
                shiny_phases.start_time,
                shiny_phases.end_time,
                shiny_phases.shiny_encounter_id,
                shiny_phases.encounters,
                shiny_phases.anti_shiny_encounters,
                shiny_phases.highest_iv_sum,
                shiny_phases.highest_iv_sum_species,
                shiny_phases.lowest_iv_sum,
                shiny_phases.lowest_iv_sum_species,
                shiny_phases.highest_sv,
                shiny_phases.highest_sv_species,
                shiny_phases.lowest_sv,
                shiny_phases.lowest_sv_species,
                shiny_phases.longest_streak,
                shiny_phases.longest_streak_species,
                shiny_phases.current_streak,
                shiny_phases.current_streak_species,
                shiny_phases.fishing_attempts,
                shiny_phases.successful_fishing_attempts,
                shiny_phases.longest_unsuccessful_fishing_streak,
                shiny_phases.current_unsuccessful_fishing_streak,
                shiny_phases.pokenav_calls,
                shiny_phases.snapshot_total_encounters,
                shiny_phases.snapshot_total_shiny_encounters,
                shiny_phases.snapshot_species_encounters,
                shiny_phases.snapshot_species_shiny_encounters,
                
                encounters.encounter_id,
                encounters.species_id,
                encounters.personality_value,
                encounters.shiny_phase_id,
                encounters.is_shiny,
                encounters.is_roamer,
                encounters.matching_custom_catch_filters,
                encounters.encounter_time,
                encounters.map,
                encounters.coordinates,
                encounters.bot_mode,
                encounters.type,
                encounters.outcome,
                encounters.data
            FROM shiny_phases
            LEFT JOIN encounters ON encounters.encounter_id = shiny_phases.shiny_encounter_id
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            {f'LIMIT {limit} OFFSET {offset}' if limit is not None else ''}
            """,
            [] if parameters is None else parameters,
        )

        for row in result:
            if row[27] is not None:
                encounter = Encounter.from_row_data(row[27:])
            else:
                encounter = None

            yield ShinyPhase.from_row_data(row[:27], encounter)

    def _query_single_shiny_phase(self, where_clause: str, parameters: tuple | None = None) -> ShinyPhase | None:
        result = list(self._query_shiny_phases(where_clause, parameters, limit=1))
        return result[0] if len(result) > 0 else None

    def _get_next_shiny_phase_id(self) -> int:
        result = self._cursor.execute(
            "SELECT shiny_phase_id FROM shiny_phases ORDER BY shiny_phase_id DESC LIMIT 1"
        ).fetchone()
        if result is None:
            return 1
        else:
            return int(result[0]) + 1

    def _get_encounter_summaries(self) -> dict[int, EncounterSummary]:
        result = self._cursor.execute(
            """
            SELECT
                species_id,
                species_name,
                total_encounters,
                shiny_encounters,
                catches,
                total_highest_iv_sum,
                total_lowest_iv_sum,
                total_highest_sv,
                total_lowest_sv,
                phase_encounters,
                phase_highest_iv_sum,
                phase_lowest_iv_sum,
                phase_highest_sv,
                phase_lowest_sv,
                last_encounter_time
            FROM encounter_summaries
            ORDER BY species_id
            """
        )

        encounter_summaries = {}
        for row in result:
            species_id = int(row[0])
            species_form = None
            if species_id >= 20100 and species_id < 20200:
                species_form = get_unown_letter_by_index(species_id - 20100)

            encounter_summaries[species_id] = EncounterSummary(
                species=get_species_by_index(species_id),
                species_form=species_form,
                total_encounters=int(row[2]),
                shiny_encounters=int(row[3]),
                catches=int(row[4]),
                total_highest_iv_sum=int(row[5]),
                total_lowest_iv_sum=int(row[6]),
                total_highest_sv=int(row[7]),
                total_lowest_sv=int(row[8]),
                phase_encounters=int(row[9]),
                phase_highest_iv_sum=int(row[10]) if row[10] is not None else None,
                phase_lowest_iv_sum=int(row[11]) if row[11] is not None else None,
                phase_highest_sv=int(row[12]) if row[12] is not None else None,
                phase_lowest_sv=int(row[13]) if row[13] is not None else None,
                last_encounter_time=datetime.fromisoformat(row[14]),
            )

        return encounter_summaries

    def _get_pickup_items(self) -> dict[int, PickupItem]:
        pickup_items = {}
        result = self._cursor.execute("SELECT item_id, item_name, times_picked_up FROM pickup_items ORDER BY item_id")
        for row in result:
            pickup_items[int(row[0])] = PickupItem(get_item_by_index(int(row[0])), int(row[2]))
        return pickup_items

    def _get_base_data(self) -> dict[str, str | None]:
        data_list = {}
        result = self._cursor.execute("SELECT data_key, value FROM base_data ORDER BY data_key")
        for row in result:
            data_list[row[0]] = row[1]
        return data_list

    def _get_last_encounter(self) -> Encounter | None:
        result = list(self.query_encounters(limit=1))
        if len(result) == 0:
            return None
        else:
            return result[0]

    def _insert_encounter(self, encounter: Encounter) -> None:
        self._execute_write(
            """
            INSERT INTO encounters
                (encounter_id, species_id, personality_value, shiny_phase_id, is_shiny, matching_custom_catch_filters, encounter_time, map, coordinates, bot_mode, type, outcome, data)
            VALUES
                (?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter.encounter_id,
                encounter.species_id,
                encounter.pokemon.personality_value,
                encounter.shiny_phase_id,
                encounter.is_shiny,
                encounter.matching_custom_catch_filters,
                encounter.encounter_time,
                encounter.map,
                encounter.coordinates,
                encounter.bot_mode,
                encounter.type.value if encounter.type else None,
                None,
                encounter.data,
            ),
        )

    def _update_encounter_outcome(self, encounter: Encounter):
        self._execute_write(
            "UPDATE encounters SET outcome = ? WHERE encounter_id = ?",
            (encounter.outcome.value, encounter.encounter_id),
        )

    def _insert_shiny_phase(self, shiny_phase: ShinyPhase) -> None:
        self._execute_write(
            "INSERT INTO shiny_phases (shiny_phase_id, start_time) VALUES (?, ?)",
            (shiny_phase.shiny_phase_id, shiny_phase.start_time),
        )

    def _update_shiny_phase(self, shiny_phase: ShinyPhase) -> None:
        self._execute_write(
            """
            UPDATE shiny_phases
            SET encounters = ?,
                anti_shiny_encounters = ?,
                highest_iv_sum = ?,
                highest_iv_sum_species = ?,
                lowest_iv_sum = ?,
                lowest_iv_sum_species = ?,
                highest_sv = ?,
                highest_sv_species = ?,
                lowest_sv = ?,
                lowest_sv_species = ?,
                longest_streak = ?,
                longest_streak_species = ?,
                current_streak = ?,
                current_streak_species = ?,
                fishing_attempts = ?,
                successful_fishing_attempts = ?,
                longest_unsuccessful_fishing_streak = ?,
                current_unsuccessful_fishing_streak = ?,
                pokenav_calls = ?,
                snapshot_total_encounters = ?,
                snapshot_total_shiny_encounters = ?,
                snapshot_species_encounters = ?,
                snapshot_species_shiny_encounters = ?
            WHERE shiny_phase_id = ?
            """,
            (
                shiny_phase.encounters,
                shiny_phase.anti_shiny_encounters,
                shiny_phase.highest_iv_sum.value if shiny_phase.highest_iv_sum is not None else None,
                shiny_phase.highest_iv_sum.species_id_for_database if shiny_phase.highest_iv_sum is not None else None,
                shiny_phase.lowest_iv_sum.value if shiny_phase.lowest_iv_sum is not None else None,
                shiny_phase.highest_iv_sum.species_id_for_database if shiny_phase.lowest_iv_sum is not None else None,
                shiny_phase.highest_sv.value if shiny_phase.highest_sv is not None else None,
                shiny_phase.highest_sv.species_id_for_database if shiny_phase.highest_sv is not None else None,
                shiny_phase.lowest_sv.value if shiny_phase.lowest_sv is not None else None,
                shiny_phase.lowest_sv.species_id_for_database if shiny_phase.lowest_sv is not None else None,
                shiny_phase.longest_streak.value if shiny_phase.longest_streak is not None else None,
                shiny_phase.longest_streak.species_id_for_database if shiny_phase.longest_streak is not None else None,
                shiny_phase.current_streak.value if shiny_phase.current_streak is not None else None,
                shiny_phase.current_streak.species_id_for_database if shiny_phase.current_streak is not None else None,
                shiny_phase.fishing_attempts,
                shiny_phase.successful_fishing_attempts,
                shiny_phase.longest_unsuccessful_fishing_streak,
                shiny_phase.current_unsuccessful_fishing_streak,
                shiny_phase.pokenav_calls,
                shiny_phase.snapshot_total_encounters,
                shiny_phase.snapshot_total_shiny_encounters,
                shiny_phase.snapshot_species_encounters,
                shiny_phase.snapshot_species_shiny_encounters,
                shiny_phase.shiny_phase_id,
            ),
        )

    def _reset_phase_in_database(self, encounter: Encounter) -> None:
        """
        Resets phase-specific information for `shiny_phases` and `encounter_summaries` table.
        :param encounter: Shiny encounter that ended the phase.
        """

        self._execute_write(
            "UPDATE shiny_phases SET end_time = ?, shiny_encounter_id = ? WHERE shiny_phase_id = ?",
            (encounter.encounter_time, encounter.encounter_id, self.current_shiny_phase.shiny_phase_id),
        )

        self._execute_write(
            """
            UPDATE encounter_summaries
               SET phase_encounters = 0,
                   phase_highest_iv_sum = NULL,
                   phase_lowest_iv_sum = NULL,
                   phase_highest_sv = NULL,
                   phase_lowest_sv = NULL
            """
        )

    def _insert_or_update_encounter_summary(self, encounter_summary: EncounterSummary) -> None:
        if encounter_summary.species is None:
            raise RuntimeError("Cannot save an encounter summary that is not associated to a species.")

        self._execute_write(
            """
            REPLACE INTO encounter_summaries
                (species_id, species_name, total_encounters, shiny_encounters, catches, total_highest_iv_sum, total_lowest_iv_sum, total_highest_sv, total_lowest_sv, phase_encounters, phase_highest_iv_sum, phase_lowest_iv_sum, phase_highest_sv, phase_lowest_sv, last_encounter_time)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter_summary.species_id_for_database,
                encounter_summary.species_name,
                encounter_summary.total_encounters,
                encounter_summary.shiny_encounters,
                encounter_summary.catches,
                encounter_summary.total_highest_iv_sum,
                encounter_summary.total_lowest_iv_sum,
                encounter_summary.total_highest_sv,
                encounter_summary.total_lowest_sv,
                encounter_summary.phase_encounters,
                encounter_summary.phase_highest_iv_sum,
                encounter_summary.phase_lowest_iv_sum,
                encounter_summary.phase_highest_sv,
                encounter_summary.phase_lowest_sv,
                encounter_summary.last_encounter_time,
            ),
        )

    def _insert_or_update_pickup_item(self, pickup_item: PickupItem) -> None:
        self._execute_write(
            "REPLACE INTO pickup_items (item_id, item_name, times_picked_up) VALUES (?, ?, ?)",
            (pickup_item.item.index, pickup_item.item.name, pickup_item.times_picked_up),
        )

    def _execute_write(self, query: str, parameters: list | tuple = ()):
        with self._lock:
            try:
                self._cursor.execute(query, parameters)
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as exception:
                self._handle_sqlite_error(exception)
                raise

    def _commit(self) -> None:
        try:
            self._connection.commit()
        except sqlite3.OperationalError as exception:
            self._handle_sqlite_error(exception)
            raise

    def _handle_sqlite_error(self, exception: sqlite3.OperationalError | sqlite3.IntegrityError) -> None:
        if exception.sqlite_errorname == "SQLITE_BUSY":
            console.print(
                "\n[bold red]Error: Stats database is locked[/]\n\n"
                "[red]We could not write to the statistics database because it is being used by another process.\n"
                "This might be because you are running the bot multiple times with the same profile, or because you "
                "have opened `stats.db` in a database editing tool.\n\n"
                "[bold]Close all instances of the bot and all associated terminal windows and close any tool that you "
                "have opened `stats.db` with and try again.[/bold]\n\n"
                "As a last resort, restarting your computer might help.[/]"
            )
            sys.exit(1)
        elif exception.sqlite_errorname == "SQLITE_CONSTRAINT_PRIMARYKEY" and "encounters.encounter_id" in str(
            exception
        ):
            console.print(
                "\n[bold red]Error: Could not write encounter to stats database.[/]\n\n"
                "[red]We could not log this encounter to the statistics database because the encounter ID we chose "
                "has already been used. This probably means that you ran multiple instances of this profile at the "
                "same time.\n\n"
                "[bold]Close all instances of the bot and try again.[/bold]\n\n"
                f"Original error: {str(exception)}[/]"
            )
            sys.exit(1)

    def _migrate_old_stats(self, profile: "Profile") -> None:
        """
        Checks whether the profile has legacy stats files (`stats/totals.json` and `stats/shiny_log.json`)
        and migrates them to the new database schema as best it can.

        :param profile: Currently loaded profile
        """

        from modules.stats.stats_migrate import migrate_file_based_stats_to_sqlite

        migrate_file_based_stats_to_sqlite(
            profile,
            self._insert_encounter,
            self._insert_shiny_phase,
            self._update_shiny_phase,
            self._insert_or_update_encounter_summary,
            self._get_encounter_summaries,
            self.query_encounters,
            self._query_shiny_phases,
            self._cursor.execute,
            self._connection.commit,
        )

    def _get_schema_version(self) -> int:
        """
        :return: The version number of the database schema, or 0 if this is a new database.
        """
        result = self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        if result.fetchone() is None:
            return 0

        result = self._cursor.execute("SELECT version FROM schema_version").fetchone()
        if result is None:
            return 0

        return int(result[0])

    def _update_schema(self, from_schema_version: int) -> None:
        """
        Updates the database schema to the current version.

        This function should contain blocks like

        ```python
            if from_schema_version <= 3:
                self._cursor.execute(...)
        ```

        and these blocks should be sorted by the `from_schema_version` value they check
        for, with the smallest number first.

        This means that even from an empty/non-existent database or any older version,
        an up-to-date schema can be created.

        :param from_schema_version: Version number of the database schema as it
                                    currently exists in the database (0 means there is
                                    no database.)
        """

        if from_schema_version <= 0:
            self._execute_write("CREATE TABLE schema_version (version INT UNSIGNED)")

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE base_data (
                        data_key INT UNSIGNED PRIMARY KEY,
                        value TEXT DEFAULT NULL
                    )
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE encounter_summaries (
                        species_id INT UNSIGNED PRIMARY KEY,
                        species_name TEXT NOT NULL,
                        total_encounters INT UNSIGNED,
                        shiny_encounters INT UNSIGNED,
                        catches INT UNSIGNED,
                        total_highest_iv_sum INT UNSIGNED,
                        total_lowest_iv_sum INT UNSIGNED,
                        total_highest_sv INT UNSIGNED,
                        total_lowest_sv INT UNSIGNED,
                        phase_encounters INT UNSIGNED,
                        phase_highest_iv_sum INT UNSIGNED DEFAULT NULL,
                        phase_lowest_iv_sum INT UNSIGNED DEFAULT NULL,
                        phase_highest_sv INT UNSIGNED DEFAULT NULL,
                        phase_lowest_sv INT UNSIGNED DEFAULT NULL,
                        last_encounter_time DATETIME
                    )
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE shiny_phases (
                        shiny_phase_id INT UNSIGNED PRIMARY KEY,
                        start_time DATETIME NOT NULL,
                        end_time DATETIME DEFAULT NULL,
                        shiny_encounter_id INT UNSIGNED DEFAULT NULL,
                        encounters INT UNSIGNED DEFAULT 0,
                        highest_iv_sum INT UNSIGNED DEFAULT NULL,
                        highest_iv_sum_species INT UNSIGNED DEFAULT NULL,
                        lowest_iv_sum INT UNSIGNED DEFAULT NULL,
                        lowest_iv_sum_species INT UNSIGNED DEFAULT NULL,
                        highest_sv INT UNSIGNED DEFAULT NULL,
                        highest_sv_species INT UNSIGNED DEFAULT NULL,
                        lowest_sv INT UNSIGNED DEFAULT NULL,
                        lowest_sv_species INT UNSIGNED DEFAULT NULL,
                        longest_streak INT UNSIGNED DEFAULT 0,
                        longest_streak_species INT UNSIGNED DEFAULT NULL,
                        current_streak INT UNSIGNED DEFAULT 0,
                        current_streak_species INT UNSIGNED DEFAULT NULL,
                        fishing_attempts INT UNSIGNED DEFAULT 0,
                        successful_fishing_attempts INT UNSIGNED DEFAULT 0,
                        longest_unsuccessful_fishing_streak INT UNSIGNED DEFAULT 0,
                        current_unsuccessful_fishing_streak INT UNSIGNED DEFAULT 0,
                        snapshot_total_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_total_shiny_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_species_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_species_shiny_encounters INT UNSIGNED DEFAULT NULL
                    )
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE encounters (
                        encounter_id INT UNSIGNED PRIMARY KEY,
                        species_id INT UNSIGNED NOT NULL,
                        personality_value INT UNSIGNED NOT NULL,
                        shiny_phase_id INT UNSIGNED NOT NULL,
                        is_shiny INT UNSIGNED DEFAULT 0,
                        is_roamer INT UNSIGNED DEFAULT 0,
                        matching_custom_catch_filters TEXT DEFAULT NULL,
                        encounter_time DATETIME NOT NULL,
                        map TEXT,
                        coordinates TEXT,
                        bot_mode TEXT,
                        type TEXT DEFAULT NULL,
                        outcome INT UNSIGNED DEFAULT NULL,
                        data BLOB NOT NULL
                    )
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE pickup_items (
                        item_id INT UNSIGNED PRIMARY KEY,
                        item_name TEXT NOT NULL,
                        times_picked_up INT NOT NULL DEFAULT 0
                    )
                    """
                )
            )

        if from_schema_version <= 1:
            self._execute_write(
                dedent(
                    """
                    ALTER TABLE shiny_phases
                        ADD pokenav_calls INT UNSIGNED DEFAULT 0
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    DROP TABLE base_data
                    """
                )
            )

            self._execute_write(
                dedent(
                    """
                    CREATE TABLE base_data (
                        data_key TEXT PRIMARY KEY,
                        value TEXT DEFAULT NULL
                    )
                    """
                )
            )

        if from_schema_version <= 2:
            self._execute_write(dedent("""
                ALTER TABLE shiny_phases
                    ADD anti_shiny_encounters INT UNSIGNED DEFAULT 0
                """))

        self._execute_write("DELETE FROM schema_version")
        self._execute_write("INSERT INTO schema_version VALUES (?)", (current_schema_version,))
        self._connection.commit()
