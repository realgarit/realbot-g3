# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.core.context import context
from modules.map.map import get_effective_encounter_rates_for_current_map, get_map_data
from modules.map.map_data import MapFRLG, MapRSE
from modules.player.player import get_player_avatar
from modules.core.state_cache import state_cache
from modules.web.state import _update_via_work_queue

route = web.RouteTableDef()


@route.get("/map")
async def http_get_map(request: web.Request):
    """
    ---
    get:
      description: Returns data about the map and current tile that the player avatar is standing on.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - map
    """

    cached_avatar = state_cache.player_avatar
    _update_via_work_queue(cached_avatar, get_player_avatar)

    if cached_avatar.value is not None:
        try:
            map_data = cached_avatar.value.map_location
            data = {
                "map": map_data.dict_for_map(),
                "player_position": map_data.local_position,
                "tiles": map_data.dicts_for_all_tiles(),
            }
        except (RuntimeError, TypeError):
            data = None
    else:
        data = None

    return web.json_response(data)


@route.get("/map_encounters")
async def http_get_map_encounters(request: web.Request):
    """
    ---
    get:
      description: >
        Returns a list of encounters (both regular and effective, i.e. taking into account
        Repel status and the lead Pokémon's level.)
      responses:
        200:
          content:
            application/json: {}
      tags:
        - map
    """

    effective_encounters = state_cache.effective_wild_encounters
    _update_via_work_queue(effective_encounters, get_effective_encounter_rates_for_current_map)

    return web.json_response(effective_encounters.value.to_dict())


@route.get("/map/{map_group:\\d+}/{map_number:\\d+}")
async def http_get_map_by_group_and_number(request: web.Request):
    """
    ---
    get:
      description: Returns detailed information about a specific map.
      parameters:
        - in: path
          name: map_group
          schema:
            type: integer
          required: true
          default: 1
          description: Map Group ID
        - in: path
          name: map_number
          schema:
            type: integer
          required: true
          default: 1
          description: Map Number ID
      responses:
        200:
          content:
            application/json: {}
      tags:
        - map
    """

    map_group = int(request.match_info["map_group"])
    map_number = int(request.match_info["map_number"])
    maps_enum = MapRSE if context.rom.is_rse else MapFRLG
    try:
        maps_enum((map_group, map_number))
    except ValueError:
        return web.Response(text=f"No such map: {map_group}, {map_number}", status=404)

    map_data = get_map_data((map_group, map_number), local_position=(0, 0))
    return web.json_response(
        {
            "map": map_data.dict_for_map(),
            "tiles": map_data.dicts_for_all_tiles(),
        }
    )
