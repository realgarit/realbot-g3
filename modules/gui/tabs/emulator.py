# Copyright (c) 2026 realgarit
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.gui.emulator_controls import DebugTab
from modules.gui.tabs.utils import FancyTreeview

if TYPE_CHECKING:
    from modules.game.libmgba import LibmgbaEmulator


class EmulatorTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        root.add(frame, text="Emulator")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data(emulator))

    def _get_data(self, emulator: "LibmgbaEmulator"):
        from modules.game.libmgba import AudioBufInfo, VideoBufInfo

        core = emulator._core

        video_buf_info = VideoBufInfo()
        core.get_video_buffer_info(video_buf_info)

        audio_buf_info = AudioBufInfo()
        core.get_audio_buffer_info(audio_buf_info)

        return {
            "Core": {
                "Desired Audio Buffer Length": core.desired_audio_buffer_length(),
                "Desired Video Buffer Length": core.desired_video_buffer_length(),
                "Frame Counter": core.frame_counter(),
                "CPU Frequency": core.frequency(),
            },
            "Video Buffer": {
                "Width": video_buf_info.width,
                "Height": video_buf_info.height,
                "Stride": video_buf_info.stride,
                "Format": video_buf_info.format,
            },
            "Audio Buffer": {
                "Frequency": audio_buf_info.frequency,
                "Samples": audio_buf_info.samples,
                "Channels": audio_buf_info.channels,
                "Format": audio_buf_info.format,
            },
        }
