🏠 [`realbot-g3` Wiki Home](../README.md)

# 🎥 OBS and HTTP Server Config

> [!NOTE]
> 🚧 **Work in Progress**: Stream integrations are currently being reworked. The settings below might change.

[`profiles/obs.yml`](../../modules/config/templates/obs.yml)

You can use this to set up stream overlays and web UIs.

## OBS Settings
### OBS WebSocket
The `obs_websocket` config lets the bot talk to OBS. Check out [obs-websocket](https://github.com/obsproject/obs-websocket) if you need more info on how that works.

Enable WebSockets in **OBS** > **Tools** > **Websocket Server Settings** > **Enable WebSocket Server**

- `host`: The IP address for OBS WebSockets.
- `port`: The port it's listening on.
- `password`: The password you set for the server (**required**).

### WebSocket Options
- `shiny_delay`: Delays the shiny catch logic by `n` frames. Good for giving viewers a moment to react before you save a replay.
- `discord_delay`: Delays Discord webhooks by `n` seconds. Helps avoid spoilers if your stream has a delay.
- `screenshot`: Takes a screenshot of the encounter.
  - This happens after `shiny_delay` so overlays have time to update.
- `replay_buffer`: Saves the OBS replay buffer.
- `replay_buffer_delay`: Delays saving the replay buffer by `n` seconds.
  - Runs in the background so it won't pause the bot.
  - If the buffer is long enough, you might catch the moments after the encounter too.
- `discord_webhook_url`: The URL to post the `screenshot` to after a shiny appearing.
