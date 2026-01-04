# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.context import context

route = web.RouteTableDef()


@route.get("/encounter_log")
async def http_get_encounter_log(request: web.Request):
    """
    ---
    get:
      description: Returns a detailed list of the recent 10 Pokémon encounters.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - stats
    """

    return web.json_response([pokemon.to_dict() for pokemon in context.stats.get_encounter_log()])


@route.get("/shiny_log")
async def http_get_shiny_log(request: web.Request):
    """
    ---
    get:
      description: Returns a detailed list of all shiny Pokémon encounters.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - stats
    """

    return web.json_response([phase.to_dict() for phase in context.stats.get_shiny_log()])


@route.get("/encounter_rate")
async def http_get_encounter_rate(request: web.Request):
    """
    ---
    get:
      description: Returns the current encounter rate (encounters per hour).
      responses:
        200:
          content:
            application/json: {}
      tags:
        - stats
    """

    return web.json_response({"encounter_rate": context.stats.encounter_rate})


@route.get("/stats")
async def http_get_stats(request: web.Request):
    """
    ---
    get:
      description: Returns returns current phase and total statistics.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - stats
    """

    return web.json_response(context.stats.get_global_stats().to_dict())
