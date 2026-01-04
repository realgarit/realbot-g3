# Copyright (c) 2026 realgarit
import asyncio
import queue
import time
from queue import Queue
from typing import Union

from aiohttp import web

from modules.core.context import context

try:
    from aiortc import MediaStreamTrack, VideoStreamTrack, RTCPeerConnection, RTCSessionDescription
    from aiortc.contrib.media import MediaRelay
    from av import VideoFrame, Packet, AudioFrame
    from av.frame import Frame

    webrtc_available = True
except ImportError:
    webrtc_available = False

route = web.RouteTableDef()

if webrtc_available:
    rtc_connections: set[RTCPeerConnection] = set()

    class EmuVideo(VideoStreamTrack):
        def __init__(self):
            super().__init__()

        async def recv(self) -> Union[Frame, Packet]:
            pts, time_base = await self.next_timestamp()

            frame = VideoFrame.from_image(context.emulator.get_current_screen_image())
            frame.pts = pts
            frame.time_base = time_base

            return frame

    class EmuAudio(MediaStreamTrack):
        kind = "audio"

        def __init__(self):
            super().__init__()
            self._queue: Queue[bytes] = context.emulator.get_last_audio_data()
            self._start: float | None = None
            self._timestamp: float = 0

        async def recv(self) -> Union[Frame, Packet]:
            sample_rate = context.emulator.get_sample_rate()
            data = b""
            while len(data) == 0:
                try:
                    part = self._queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(1 / 480)
                    continue
                data += part

            if self._start is None:
                self._start = time.time()

            frame = AudioFrame(format="s16", layout="stereo", samples=len(data) // 4)
            frame.planes[0].update(data)
            frame.pts = self._timestamp
            frame.sample_rate = sample_rate

            self._timestamp += len(data) // 4

            return frame

    relay = MediaRelay()
    emu_audio = None
    emu_video = None

    @route.post("/rtc")
    async def http_post_rtc(request: web.Request):
        global rtc_connections, emu_video, emu_audio

        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        connection = RTCPeerConnection()
        rtc_connections.add(connection)

        @connection.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message):
                if isinstance(message, str) and message.startswith("ping"):
                    channel.send("pong" + message[4:])

        @connection.on("connectionstatechange")
        async def on_connection_state_change():
            if connection.connectionState == "failed":
                await connection.close()
                rtc_connections.discard(connection)

        if emu_video is None:
            emu_video = EmuVideo()

        if emu_audio is None:
            emu_audio = EmuAudio()

        connection.addTrack(relay.subscribe(emu_video))
        connection.addTrack(relay.subscribe(emu_audio))

        await connection.setRemoteDescription(offer)

        answer = await connection.createAnswer()
        await connection.setLocalDescription(answer)

        return web.json_response({"sdp": connection.localDescription.sdp, "type": connection.localDescription.type})

else:

    @route.post("/rtc")
    async def http_post_rtc(request: web.Request):
        return web.Response(
            text="WebRTC is not available because aiortc was not installed.",
            status=503,
            headers={"Content-Type": "text/plain"},
        )
