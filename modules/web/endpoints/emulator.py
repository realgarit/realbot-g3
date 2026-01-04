# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.core.context import context
from modules.modes import get_bot_mode_names

route = web.RouteTableDef()


@route.get("/fps")
async def http_get_fps(request: web.Request):
    """
    ---
    get:
      description: Returns a list of emulator FPS (frames per second), in intervals of 1 second, for the previous 60 seconds.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """

    if context.emulator is None:
        return web.json_response(None)
    else:
        return web.json_response(list(reversed(context.emulator._performance_tracker.fps_history)))


@route.get("/bot_modes")
async def http_get_bot_modes(request: web.Request):
    """
    ---
    get:
      description: Returns a list of installed bot modes.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """
    return web.json_response(get_bot_mode_names())


@route.get("/emulator")
async def http_get_emulator(request: web.Request):
    """
    ---
    get:
      description: Returns information about the emulator core + the current loaded game/profile.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """

    if context.emulator is None:
        return web.json_response(None)
    else:
        return web.json_response(
            {
                "emulation_speed": context.emulation_speed,
                "video_enabled": context.video,
                "audio_enabled": context.audio,
                "bot_mode": context.bot_mode,
                "current_message": context.message,
                "frame_count": context.emulator.get_frame_count(),
                "current_fps": context.emulator.get_current_fps(),
                "current_time_spent_in_bot_fraction": context.emulator.get_current_time_spent_in_bot_fraction(),
                "profile": {"name": context.profile.path.name},
                "game": {
                    "title": context.rom.game_title,
                    "name": context.rom.game_name,
                    "language": str(context.rom.language),
                    "revision": context.rom.revision,
                },
            }
        )


@route.post("/emulator")
async def http_post_emulator(request: web.Request):
    """
    ---
    post:
      description: Change some settings for the emulator. Accepts a JSON payload.
      requestBody:
        description: JSON payload
        content:
          application/json:
            schema: {}
            examples:
              emulation_speed:
                summary: Set emulation speed to 4x
                value: {"emulation_speed": 4}
              bot_mode:
                summary: Set bot bode to spin
                value: {"bot_mode": "Spin"}
              video_enabled:
                summary: Enable video
                value: {"video_enabled": true}
              audio_enabled:
                summary: Disable audio
                value: {"audio_enabled": false}
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """

    new_settings = await request.json()
    if not isinstance(new_settings, dict):
        return web.Response(text="This endpoint expects a JSON object as its payload.", status=422)

    for key in new_settings:
        if key == "emulation_speed":
            if new_settings["emulation_speed"] not in [0, 1, 2, 3, 4, 8, 16, 32]:
                return web.Response(
                    text=f"Setting `emulation_speed` contains an invalid value ('{new_settings['emulation_speed']}')",
                    status=422,
                )
            context.emulation_speed = new_settings["emulation_speed"]
        elif key == "bot_mode":
            if new_settings["bot_mode"] not in get_bot_mode_names():
                return web.Response(
                    text=f"Setting `bot_mode` contains an invalid value ('{new_settings['bot_mode']}'). Possible values are: {', '.join(get_bot_mode_names())}",
                    status=422,
                )
            context.bot_mode = new_settings["bot_mode"]
        elif key == "video_enabled":
            if not isinstance(new_settings["video_enabled"], bool):
                return web.Response(
                    text="Setting `video_enabled` did not contain a boolean value.",
                    status=422,
                )
            context.video = new_settings["video_enabled"]
        elif key == "audio_enabled":
            if not isinstance(new_settings["audio_enabled"], bool):
                return web.Response(
                    text="Setting `audio_enabled` did not contain a boolean value.",
                    status=422,
                )
            context.audio = new_settings["audio_enabled"]
        else:
            return web.Response(text=f"Unrecognised setting: '{key}'.", status=422)

    return await http_get_emulator(request)
