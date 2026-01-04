# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.core.context import context
from modules.game.libmgba import inputs_to_strings
from modules.core.main import work_queue

route = web.RouteTableDef()


@route.get("/input")
async def http_get_input(request: web.Request):
    """
    ---
    get:
      description: Returns a list of currently pressed buttons.
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """
    return web.json_response(inputs_to_strings(context.emulator.get_inputs()))


@route.post("/input")
async def http_post_input(request: web.Request):
    """
    ---
    post:
      description: Sets which buttons are being pressed. Accepts a JSON payload.
      requestBody:
        description: JSON payload
        content:
          application/json:
            schema: {}
            examples:
              press_right_and_b:
                summary: Press Right an B
                value: ["B", "Right"]
              release_all_buttons:
                summary: Release all buttons
                value: []
      responses:
        200:
          content:
            application/json: {}
      tags:
        - emulator
    """
    new_buttons = await request.json()
    if not isinstance(new_buttons, list):
        return web.Response(text="This endpoint expects a JSON array as its payload.", status=422)

    possible_buttons = ["A", "B", "Select", "Start", "Right", "Left", "Up", "Down", "R", "L"]
    buttons_to_press = []
    for button in new_buttons:
        for possible_button in possible_buttons:
            if button.lower() == possible_button.lower():
                buttons_to_press.append(possible_button)

    def update_inputs():
        if context.bot_mode == "Manual":
            context.emulator.reset_held_buttons()
            for button_to_press in buttons_to_press:
                context.emulator.hold_button(button_to_press)

    work_queue.put_nowait(update_inputs)

    return web.Response(status=204)
