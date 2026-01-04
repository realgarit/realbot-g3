# Copyright (c) 2026 realgarit
from aiohttp import web

from modules.runtime import get_base_path

route = web.RouteTableDef()


@route.get("/docs")
async def http_docs(request: web.Request):
    raise web.HTTPFound(location="/static/api-doc.html")


@route.get("/stream-overlay")
@route.get("/static/stream-overlay")
@route.get("/static/stream-overlay/")
async def http_stream_overlay_redirect(request: web.Request):
    return web.HTTPFound(location="/static/stream-overlay/index.html")


@route.get("/")
async def http_index(request: web.Request):
    raise web.HTTPFound(location="/static/index.html")


# We can register the static route here or in http.py, but since it's "meta", 
# sticking it to the mix or handling it in http.py is fine. 
# http.py handles static routes registration usually.
