🏠 [`realbot-g3` Wiki Home](../README.md)

# 📢 Discord Config

[`profiles/discord.yml`](../../modules/config/templates/discord.yml)

You can use Discord integration to get shiny notifications, phase stats, and milestone updates.

For privacy, all webhooks and rich presence features are **disabled** by default.

## Discord Rich Presence
- `rich_presence`: Show your bot status on your Discord profile (game, route, encounter count, etc.).
  - Discord needs to be running on the same PC.
  - Only enable this for one bot profile at a time to avoid conflicts.

## Discord Webhooks
- `global_webhook_url`: The main URL for your Discord webhook.
  - To make one: **Edit Channel** > **Integrations** > **Webhooks** > **New Webhook**.
  - ⚠ **Warning**: Keep this URL secret so others can't post to your channel.

- `delay`: Number of seconds to wait before posting. Good for avoiding spoilers on stream.

- `bot_id`: A custom string added to the footer of messages. Useful if you have multiple bots running and want to tell them apart.

### Webhook Parameters
- `enable`: Turn the specific webhook on or off.

- `webhook_url`: Use a different URL for specific message types (overrides the global one).
  - Uncomment the line in the config file to use it.

- `ping_mode`: Set to `user` or `role` to ping someone. Leave blank to disable pings.

- `ping_id`: The ID of the user or role to ping.
  - You need Developer Mode enabled in Discord to copy this ID (Right click user/role > **Copy ID**).

### Webhook Types
- `shiny_pokemon_encounter`: Posts when a shiny Pokémon appears.

- `blocked_shiny_encounter`: Posts when a shiny appears but is skipped because it's on your block list.

- `pokemon_encounter_milestones`: Posts every `interval` encounters (e.g., every 1,000 encounters).

- `shiny_pokemon_encounter_milestones`: Posts every `interval` shiny encounters.

- `total_encounter_milestones`: Posts when the total encounter count hits a milestone.

- `phase_summary`: Posts a summary of the current phase.
  - First post at `first_interval`, then every `consequent_interval` after that.
  - Useful for keeping track of long hunts.

- `anti_shiny_pokemon_encounter`: Posts "anti-shiny" encounters.
  - These are Pokémon with an SV that is mathematically the opposite of a shiny (65,528 to 65,535). Just for fun.

- `custom_filter_pokemon_encounter`: Posts encounters that match your custom catch filters.

- `pickup`: Posts when the Pickup ability grabs an item.
  - Summarizes items every `interval` new items.

- `tcg_cards`: Posts a TCG card image corresponding to the Pokémon you encountered.

