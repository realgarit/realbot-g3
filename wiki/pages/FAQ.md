🏠 [`realbot-g3` Wiki Home](../README.md)

# ❓ General FAQ

Frequently asked questions about RealBot G3, key terms, and game mechanics.

## Glossary

### Phase
A term used by shiny hunters to refer to the number of Pokémon encountered since the last shiny.
- For example, if you found a shiny Wurmple after 8,931 encounters, you have now ‘**phased**’, and the counter resets to zero.

### SV (Shiny Value)
A number between `0` and `65,535` calculated from a Pokémon's Personality ID (PID).
- In Gen 3, if this number is **less than `8`**, the Pokémon is shiny.
- See the [Bulbapedia page](https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess) for more.

### TID and SID
Your **Trainer ID** and **Secret ID**. These are assigned at the start of the game and are used to determine if a wild Pokémon is shiny.
- See the [Bulbapedia Page](https://bulbapedia.bulbagarden.net/wiki/Trainer_ID_number) for more.

### PID (Personality ID)
A number the game assigns when generating a Pokémon. It determines properties like gender, nature, ability, and shininess.
- See the [Bulbapedia Page](https://bulbapedia.bulbagarden.net/wiki/Personality_value) for more.

## Bot Mechanics

### Why does the bot lead with specific Pokémon?
- **Cry Length**: The bot may prioritize Pokémon with shorter cries (like Lotad) to save fractions of a second per encounter.
- **Run Success**: In caves, the battle transition is shorter if your lead Pokémon is lower level than the opponent. To ensure escape, we use a low-level Pokémon with high speed (like Taillow) or a Smoke Ball.

### What are 'Illuminate' and 'White Flute'?
- **Illuminate**: An ability that doubles the encounter rate for every step.
- **White Flute**: An item that doubles encounter odds when used.
Using both reduces the number of steps/spins needed to find a Pokémon.

### Does the bot catch every shiny?
**Yes**, the bot is designed to catch every shiny it encounters.

### How does the bot hunt for static encounters (e.g. Rayquaza)?
It uses the standard run-away or soft-reset method depending on the mode selected.

### Will the bot use the Repel Trick?
**Yes**, where possible.
The Repel Trick works with both `spin` and `bunny hop` modes. By using a lead Pokémon of a specific level (e.g., Level 7), you can filter out lower-level spawns (e.g., Level 4-6) to increase the odds of encountering specific higher-level targets.

## Random Stats

### What is the chance of a shiny Pokémon in Emerald?
**1 in 8,192** (Standard Gen 3 odds).
Rates cannot be increased by Shiny Charm or Masuda Method in this generation.

### What is the chance of Pokérus?
**1 in 21,845**

### What is the chance of 6 perfect IVs?
**1 in 1,073,741,824**

### What is the chance of a shiny with 6 perfect IVs?
**1 in 8,796,093,000,000**

## Seedot Facts
People ask about this a lot.

### What are the odds?
Seedot is a **1% encounter**. That means the chance of finding a shiny one is **1 in 819,200**.

### Can't you go somewhere else?
Nope. It's a **1% encounter** everywhere it appears in the game. Same thing for Nuzleaf. We're stuck with these odds.

### What about the in-game trade?
That trade gives you DOTS. He's never shiny.

**The details:** The game sets everything about DOTS before you even trade. His stats and shininess are locked. Since the trader's ID helps determine shininess and it's fixed, DOTS will always be the exact same non-shiny Pokémon.

**For nerds:** DOTS is always Male, Level 4, Relaxed nature. PID `00000084`. OT `KOBE` (TID `38726`, SID `00000`).
