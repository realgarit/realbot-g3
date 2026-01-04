# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.game.game import _event_flags
from modules.game.memory import get_event_flag, get_game_state
from modules.web.state import custom_state

route = web.RouteTableDef()


@route.get("/game_state")
async def http_get_game_state(request: web.Request):
    """
    ---
    get:
      description: Returns game state information.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - game
    """
    game_state = get_game_state()
    if game_state is not None:
        game_state = game_state.name

    return web.json_response(game_state)


@route.get("/custom_state")
async def http_get_custom_state(request: web.Request):
    """
    ---
    get:
      description: >
        Returns a dictionary that can be filled with arbitrary data by bot plugins.
        The bot itself will not use this.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - stats
    """
    return web.json_response(custom_state)


@route.get("/event_flags")
async def http_get_event_flags(request: web.Request):
    """
    ---
    get:
      description: Returns all event flags for the current save file (optional parameter `?flag=FLAG_NAME` to get a specific flag).
      parameters:
        - in: query
          name: flag
          schema:
            type: string
          required: false
          description: flag_name
      responses:
        200:
          content:
            application/json: {}
      tags:
        - game
    """

    flag = request.query.getone("flag", None)

    if flag and flag in _event_flags:
        return web.json_response({flag: get_event_flag(flag)})
    result = {}

    for flag in _event_flags:
        result[flag] = get_event_flag(flag)

    return web.json_response(result)
