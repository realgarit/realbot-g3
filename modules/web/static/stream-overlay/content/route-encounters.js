import {
    colouredIVSum,
    colouredShinyValue,
    formatInteger,
    speciesSprite,
    renderTableRow,
    br,
    small,
    getSpeciesGoal, overlaySprite, getEmptySpeciesEntry, getSpeciesCatches
} from "../helper.js";

const mapNameSpan = document.querySelector("#map-name") ?? document.querySelector("#route-encounters > h2 > span");
const antiShinyCounter = document.querySelector("#anti-shiny-counter");
const tbody = document.querySelector("#route-encounters tbody");
const table = document.querySelector("#route-encounters table");
const noEncountersMessage = document.querySelector("#no-encounters-on-this-route-message");

/**
 * @param {RealbotApi.GetMapResponse} map
 */
const updateMapName = map => {
    mapNameSpan.innerText = map.map.pretty_name;
};

/**
 * @param {OverlayState} state
 * @return {MapEncounter[]}
 */
const getEncounterList = (state) => {
    /** @type {MapEncounter[]} encounterList */
    let encounterList;
    /** @type {MapEncounter[]} regularEncounterList */
    let regularEncounterList;
    if (state.daycareMode || state.emulator.bot_mode.toLowerCase().includes("daycare") || state.emulator.bot_mode.toLowerCase().includes("kecleon")) {
        encounterList = [];
        regularEncounterList = [];
    } else if (state.lastEncounterType === "surfing") {
        encounterList = [...state.mapEncounters.effective.surf_encounters];
        regularEncounterList = [...state.mapEncounters.regular.surf_encounters];
    } else if (state.lastEncounterType === "fishing_old_rod") {
        encounterList = [...state.mapEncounters.effective.old_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.old_rod_encounters];
    } else if (state.lastEncounterType === "fishing_good_rod") {
        encounterList = [...state.mapEncounters.effective.good_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.good_rod_encounters];
    } else if (state.lastEncounterType === "fishing_super_rod") {
        encounterList = [...state.mapEncounters.effective.super_rod_encounters];
        regularEncounterList = [...state.mapEncounters.regular.super_rod_encounters];
    } else if (state.lastEncounterType === "rock_smash") {
        encounterList = [...state.mapEncounters.effective.rock_smash_encounters];
        regularEncounterList = [...state.mapEncounters.regular.rock_smash_encounters];
    } else {
        encounterList = [...state.mapEncounters.effective.land_encounters];
        regularEncounterList = [...state.mapEncounters.regular.land_encounters];
    }

    // Add species that could appear on this map but are currently blocked by Repel and
    // therefore not part of the "effective encounters" list.
    for (const regularEncounter of regularEncounterList) {
        let alreadyInList = false;
        for (const encounterSpecies of encounterList) {
            if (encounterSpecies.species_name === regularEncounter.species_name) {
                alreadyInList = true;
            }
        }

        if (!alreadyInList) {
            encounterList.push({
                species_name: regularEncounter.species_name,
                max_level: regularEncounter.max_level,
                encounter_rate: 0
            });
        }
    }

    // Add species to this list that have been encountered here but are not part of the
    // regular encounter table (i.e. egg hatches, gift Pokémon, ...)
    for (const speciesName of state.additionalRouteSpecies) {
        let alreadyInList = false;
        for (const encounterSpecies of encounterList) {
            if (encounterSpecies.species_name === speciesName) {
                alreadyInList = true;
            }
        }

        if (!alreadyInList) {
            encounterList.push({species_name: speciesName, encounter_rate: 0});
        }
    }

    if (state.emulator.bot_mode.toLowerCase().includes("feebas") && ["surfing", "fishing_old_rod", "fishing_good_rod", "fishing_super_rod"].includes(state.lastEncounterType)) {
        let hasRecentlySeenFeebas = false;
        for (const recentEncounter of state.encounterLog) {
            if (recentEncounter.pokemon.species.name === "Feebas") {
                hasRecentlySeenFeebas = true;
                break;
            }
        }

        if (hasRecentlySeenFeebas) {
            let newEncounterList = [];
            for (const encounter of encounterList) {
                const newEncounter = {...encounter};
                newEncounter.encounter_rate /= 2;
                newEncounterList.push(newEncounter);
            }
            newEncounterList.push({
                species_id: 328,
                species_name: "Feebas",
                min_level: 20,
                max_level: 25,
                encounter_rate: 0.5
            });
            encounterList = newEncounterList;
        }
    }

    return encounterList;
}

/**
 * @typedef {Object} RouteEncounterEntry
 * @property {string} species_name
 * @property {number} encounter_rate
 * @property {number} goal
 * @property {number} catches
 * @property {number} total_encounters
 * @property {number} shiny_encounters
 * @property {number} phase_encounters
 * @property {number} phase_lowest_sv
 * @property {number} phase_highest_sv
 * @property {number} phase_lowest_iv_sum
 * @property {number} phase_highest_iv_sum
 * @property {number} shinyTargetCount
 */

/**
 * @param {RouteEncounterEntry[]} encountersList
 */
const renderRouteEncountersList = (encountersList) => {
    // Display a "no encounters on this map" message if no encounters exist at all.
    if (encountersList.length === 0) {
        noEncountersMessage.style.display = "block";
        table.style.display = "none";
        return;
    }

    noEncountersMessage.style.display = "none";
    table.style.display = "table";

    tbody.innerHTML = "";

    let hasAtLeastOneAnti = false;
    let hasPossibleEncounterThatIsNotAnti = false;
    for (const entry of encountersList) {
        if (entry.phase_highest_sv > 65527) {
            hasAtLeastOneAnti = true;
        }
        if (entry.encounter_rate > 0 && entry.phase_highest_sv < 65528) {
            hasPossibleEncounterThatIsNotAnti = true;
        }
    }

    for (const entry of encountersList) {
        let catches = [formatInteger(entry.catches)];
        let totalEncounters = [formatInteger(entry.total_encounters)];

        if (entry.goal) {
            catches = [formatInteger(entry.catches), small(`/ ${entry.goal}`)];
        }

        if (entry.shiny_encounters > 0) {
            const shinyRate = Math.round(entry.total_encounters / entry.shiny_encounters).toLocaleString("en");
            const shinyRateLabel = document.createElement("span");
            shinyRateLabel.classList.add("shiny-rate");
            const sparkles = overlaySprite("sparkles");
            shinyRateLabel.append("(", sparkles, ` 1/${shinyRate})`);
            totalEncounters.push(shinyRateLabel);
        }

        if (entry.shiny_encounters > entry.catches) {
            const missedShinies = entry.shiny_encounters - entry.catches;
            const missedShiniesLabel = document.createElement("span");
            missedShiniesLabel.classList.add("missed-shinies")
            missedShiniesLabel.textContent = `(${formatInteger(missedShinies)} missed)`;
            catches.push(missedShiniesLabel);
        }

        for (let index = 0; index < entry.shinyTargetCount; index++) {
             const tick = document.createElement("img")
             tick.src = "/static/sprites/stream-overlay/tick.png";
             tick.classList.add("tick");
             catches.push(tick);
        }

        if (entry.goal && entry.catches < entry.goal) {
            const tick = document.createElement("img")
            tick.src = "/static/sprites/stream-overlay/target.png";
            tick.classList.add("tick");
            catches.push(tick);
        }

        let spriteType = "normal";
        if (entry.phase_highest_sv > 65527) {
            spriteType = "anti-shiny";
        }
        if (entry.encounter_rate <= 0 && hasAtLeastOneAnti && !hasPossibleEncounterThatIsNotAnti) {
            spriteType = "anti-shiny";
        }

        const row = renderTableRow({
            sprite: speciesSprite(entry.species_name, spriteType),
            odds: entry.encounter_rate > 0 ? Math.round(entry.encounter_rate * 100) + "%" : "",
            svRecords: entry.phase_lowest_sv && entry.phase_highest_sv
                ? [colouredShinyValue(entry.phase_lowest_sv), br(), colouredShinyValue(entry.phase_highest_sv)]
                : "",
            ivRecords: entry.phase_highest_iv_sum && entry.phase_lowest_iv_sum
                ? [colouredIVSum(entry.phase_highest_iv_sum), br(), colouredIVSum(entry.phase_lowest_iv_sum)]
                : "",
            phaseEncounters: entry.phase_encounters > 0
                ? [
                    formatInteger(entry.phase_encounters),
                    br(),
                    small((100 * entry.phase_encounters / window.overlayState.stats.current_phase.encounters).toLocaleString("en", {maximumFractionDigits: 2}) + "%"),
                ]
                : "0",
            totalEncounters: totalEncounters,
            catches: catches,
        });
        row.dataset.speciesName = entry.species_name;
        tbody.append(row);
    }
}

/**
 * @param {string} speciesName
 */
const animateRouteEncounterSprite = (speciesName) => {
    const row = tbody.querySelector(`tr[data-species-name="${speciesName}"]`);
    if (row) {
        const sprite = row.querySelector(".column-sprite img");
        if (sprite) {
            sprite.classList.remove("animate");
            void sprite.offsetWidth;
            sprite.classList.add("animate");
        }
    }
}

/**
 * @param {OverlayState} state
 * @param {StreamOverlay.SectionChecklist} checklistConfig
 */
const updateRouteEncountersList = (state, checklistConfig) => {
    const encounterList = getEncounterList(state);

    /** @type {{[k: string]: RouteEncounterEntry}} */
    const routeEncounters = {};
    for (const encounter of encounterList) {
        const species = state.stats.pokemon[encounter.species_name] ?? getEmptySpeciesEntry(encounter.species_id, encounter.species_name);

        routeEncounters[encounter.species_name] = {
            species_name: encounter.species_name,
            encounter_rate: encounter.encounter_rate,
            goal: getSpeciesGoal(encounter.species_name, checklistConfig),
            catches: species.catches,
            total_encounters: species.total_encounters,
            shiny_encounters: species.shiny_encounters,
            phase_encounters: species.phase_encounters,
            phase_lowest_sv: species.phase_lowest_sv,
            phase_highest_sv: species.phase_highest_sv,
            phase_lowest_iv_sum: species.phase_lowest_iv_sum,
            phase_highest_iv_sum: species.phase_highest_iv_sum,
            shinyTargetCount: 0,
        };
    }

    for (const entry of Object.values(routeEncounters)) {
        if (entry.goal) {
            const avoidCountingSpecies = Object.values(routeEncounters)
                .filter(otherEntry => otherEntry.species_name !== entry.species_name && getSpeciesGoal(otherEntry.species_name, checklistConfig) > 0)
                .map(otherEntry => otherEntry.species_name);

            entry.catches = getSpeciesCatches(entry.species_name, checklistConfig, state.stats, avoidCountingSpecies);
            entry.shinyTargetCount = Math.min(entry.catches, entry.goal);

            if (entry.catches > entry.goal) {
                let alternativeExcess = entry.catches - entry.goal;
                for (const alternative of Object.values(routeEncounters).filter(other => other.species_name !== entry.species_name && getSpeciesGoal(other.species_name, checklistConfig) === entry.goal && other.catches < other.goal)) {
                    alternativeExcess--;
                    alternative.shinyTargetCount++;
                    entry.shinyTargetCount--;
                }
            }
        }
    }

    renderRouteEncountersList(Object.values(routeEncounters));

    if (cachedAntiShinyCount !== state.stats.current_phase.anti_shiny_encounters) {
        cachedAntiShinyCount = state.stats.current_phase.anti_shiny_encounters;
        antiShinyCounter.textContent = "";
        if (cachedAntiShinyCount > 0) {
            const sparkles = [];
            for (let index = 0; index < cachedAntiShinyCount; index++) {
                const img = document.createElement("img");
                img.src = "/static/sprites/stream-overlay/anti-shiny.png";
                img.alt = "";
                sparkles.push(img);
            }
            antiShinyCounter.append(...sparkles);
        }
    }
}

export {updateMapName, animateRouteEncounterSprite, updateRouteEncountersList};
