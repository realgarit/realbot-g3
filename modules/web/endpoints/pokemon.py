# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.daycare import get_daycare_data
from modules.memory import GameState
from modules.pokedex import get_pokedex
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.state_cache import state_cache
from modules.web.state import _update_via_work_queue

route = web.RouteTableDef()


@route.get("/party")
async def http_get_party(request: web.Request):
    """
    ---
    get:
      description: Returns a detailed list of all Pokémon in the party.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - pokemon
    """
    cached_party = state_cache.party
    _update_via_work_queue(cached_party, get_party)

    return web.json_response(cached_party.value.to_list())


@route.get("/pokedex")
async def http_get_pokedex(request: web.Request):
    """
    ---
    get:
      description: Returns the player's Pokédex (seen/caught).
      responses:
        200:
          content:
            application/json: {}
      tags:
        - pokemon
    """

    cached_pokedex = state_cache.pokedex
    if cached_pokedex.age_in_seconds > 1:
        _update_via_work_queue(cached_pokedex, get_pokedex)

    return web.json_response(cached_pokedex.value.to_dict())


@route.get("/pokemon_storage")
async def http_get_pokemon_storage(request: web.Request):
    """
    ---
    get:
      description: Returns detailed information about all boxes in PC storage.
      parameters:
        - in: query
          name: format
          schema:
            type: string
          required: false
          description: >
            If this is set to `size-only` the endpoint will only report the
            number of Pokémon, not the full data.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - pokemon
    """

    cached_storage = state_cache.pokemon_storage
    _update_via_work_queue(cached_storage, get_pokemon_storage)

    if "format" in request.query and request.query.getone("format") == "size-only":
        return web.json_response(
            {
                "pokemon_stored": cached_storage.value.pokemon_count,
                "boxes": [len(box.slots) for box in cached_storage.value.boxes],
            }
        )
    else:
        return web.json_response(cached_storage.value.to_dict())


@route.get("/daycare")
async def http_get_daycare(request: web.Request):
    """
    ---
    get:
      description: Returns information about which Pokémon have been deposited in the Daycare.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - pokemon
    """
    return web.json_response(get_daycare_data().to_dict())


@route.get("/opponent")
async def http_get_opponent(request: web.Request):
    """
    ---
    get:
      description: Returns detailed information about the current/recent encounter.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - pokemon
    """

    if state_cache.game_state.value != GameState.BATTLE:
        result = None
    else:
        cached_opponent = state_cache.opponent
        if cached_opponent.value is not None:
            result = cached_opponent.value[0].to_dict()
        else:
            result = None

    return web.json_response(result)
