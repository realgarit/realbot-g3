# Copyright (c) 2026 realgarit
import asyncio
import io
import queue

import aiohttp.client_exceptions
from aiohttp import web

from modules.core.context import context
from modules.web.http_stream import add_subscriber

route = web.RouteTableDef()


@route.get("/stream_events")
async def http_get_events_stream(request: web.Request):
    subscribed_topics = request.query.getall("topic")
    if len(subscribed_topics) == 0:
        return web.Response(
            text="You need to provide at least one `topic` parameter in the query.",
            status=422,
        )

    try:
        message_queue, unsubscribe, new_message_event = add_subscriber(subscribed_topics)
    except ValueError as e:
        return web.Response(text=str(e), status=422)

    response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
    await response.prepare(request)
    try:
        await response.write(b"retry: 2500\n\n")
        while True:
            await new_message_event.wait()
            try:
                while True:
                    message = message_queue.get(block=False)
                    await response.write(str.encode(message) + b"\n\n")
            except queue.Empty:
                pass
            new_message_event.clear()
    except GeneratorExit:
        await response.write_eof()
    except aiohttp.client_exceptions.ClientError:
        pass
    finally:
        unsubscribe()

    return response


@route.get("/stream_video")
async def http_get_video_stream(request: web.Request):
    """
    ---
    get:
      description: Stream emulator video.
      parameters:
        - in: query
          name: fps
          schema:
            type: integer
          required: true
          description: fps
          default: 30
      responses:
        200:
          content:
            text/event-stream:
              schema:
                type: array
      tags:
        - streams
    """
    fps = request.query.getone("fps", "30")
    fps = int(fps) if fps.isdigit() else 30
    fps = min(fps, 60)

    response = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
    await response.prepare(request)

    sleep_after_frame = 1 / fps
    png_data = io.BytesIO()
    try:
        while True:
            if context.video:
                png_data.seek(0)
                context.emulator.get_current_screen_image().convert("RGB").save(png_data, format="PNG")
                png_data.seek(0)
                await response.write(b"\r\n--frame\r\nContent-Type: image/png\r\n\r\n" + png_data.read())
            await asyncio.sleep(sleep_after_frame)
    except aiohttp.client_exceptions.ClientError:
        pass

    return response
