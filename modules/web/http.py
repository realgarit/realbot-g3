# Copyright (c) 2026 realgarit
import asyncio
import re
from threading import Thread

from aiohttp import web
from apispec import APISpec
from apispec.yaml_utils import load_operations_from_docstring

from modules.core.runtime import get_base_path
from modules.core.version import realbot_name, realbot_version
from modules.web.endpoints.controls import route as controls_route
from modules.web.endpoints.emulator import route as emulator_route
from modules.web.endpoints.game import route as game_route
from modules.web.endpoints.map import route as map_route
from modules.web.endpoints.meta import route as meta_route
from modules.web.endpoints.player import route as player_route
from modules.web.endpoints.pokemon import route as pokemon_route
from modules.web.endpoints.rtc import route as rtc_route
from modules.web.endpoints.stats import route as stats_route
from modules.web.endpoints.stream import route as stream_route
from modules.web.state import custom_state  # noqa: F401


def http_server(host: str, port: int) -> web.AppRunner:
    """
    Run Flask server to make bot data available via HTTP requests.
    """

    all_routes = [
        controls_route,
        emulator_route,
        game_route,
        map_route,
        meta_route,
        player_route,
        pokemon_route,
        rtc_route,
        stats_route,
        stream_route,
    ]

    spec = APISpec(
        title=f"{realbot_name} API",
        version=realbot_version,
        openapi_version="3.0.3",
        info=dict(
            description=f"{realbot_name} API",
            version=realbot_version,
            license=dict(
                name="GNU General Public License v3.0",
                url="https://github.com/realgar/realbot-g3/blob/main/LICENSE",
            ),
        ),
        servers=[
            dict(
                description=f"{realbot_name} server",
                url=f"http://{host}:{port}",
            )
        ],
    )

    # Everything until here is considered an API route that should be documented in Swagger.
    for route_def in all_routes:
        for api_route in route_def:
            if isinstance(api_route, web.RouteDef):
                path = re.sub("\\{([_a-zA-Z0-9]+)(:[^}]*)?}", "{\\1}", api_route.path)
                operations = load_operations_from_docstring(api_route.handler.__doc__)
                spec.path(path=path, operations=operations)

    # From here on out, any additional routes will NOT be documented in Swagger.
    async def http_get_api_json(request: web.Request):
        api_docs = spec.to_dict()
        api_docs["servers"][0]["url"] = f"http://{request.headers['host']}"

        return web.json_response(api_docs)

    server = web.Application()
    for route_def in all_routes:
        server.add_routes(route_def)

    server.add_routes([web.get("/api.json", http_get_api_json)])
    server.router.add_static("/static", get_base_path() / "modules" / "web" / "static")

    return web.AppRunner(server)


def start_http_server(host: str, port: int):
    web_app = http_server(host, port)

    def run_server(runner: web.AppRunner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        server = web.TCPSite(runner, host, port)
        loop.run_until_complete(server.start())
        loop.run_forever()

    Thread(target=run_server, args=(web_app,)).start()
