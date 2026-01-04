# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.items import get_item_bag
from modules.player import get_player, get_player_avatar
from modules.state_cache import state_cache
from modules.web.state import _update_via_work_queue

route = web.RouteTableDef()


@route.get("/player")
async def http_get_player(request: web.Request):
    """
    ---
    get:
      description:
        Returns player rarely-changing player data such as name, TID, SID etc.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - player
    """

    def do_update():
        get_player()

    _update_via_work_queue(state_cache.player, do_update)

    if state_cache.player.value:
        return web.json_response(
            {
                "name": state_cache.player.value.name,
                "gender": state_cache.player.value.gender,
                "trainer_id": state_cache.player.value.trainer_id,
                "secret_id": state_cache.player.value.secret_id,
                "money": state_cache.player.value.money,
                "coins": state_cache.player.value.coins,
                "registered_item": (
                    state_cache.player.value.registered_item.name
                    if state_cache.player.value.registered_item
                    else None
                ),
            }
        )
    return web.json_response(None)


@route.get("/player/avatar")
async def http_get_player_avatar(request: web.Request):
    """
    ---
    get:
      description: Returns player avatar data, on-map character data such as map bank, map ID, X/Y coordinates
      responses:
        200:
          content:
            application/json: {}
      tags:
        - player
    """

    def do_update():
        get_player_avatar()

    _update_via_work_queue(state_cache.player_avatar, do_update, maximum_age_in_frames=1)

    if state_cache.player_avatar.value:
        return web.json_response(state_cache.player_avatar.value.to_dict())
    return web.json_response(None)


@route.get("/bag")
async def http_get_bag(request: web.Request):
    """
    ---
    get:
      description: Returns a list of all items in the bag and PC, and their quantities.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - player
    """

    def do_update():
        get_item_bag()

    _update_via_work_queue(state_cache.item_bag, do_update)

    if state_cache.item_bag.value:
        return web.json_response(state_cache.item_bag.value.to_dict())
    return web.json_response(None)
