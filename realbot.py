# Copyright (c) 2026 realgarit
"""Main program entrypoint."""

import argparse
import atexit
import os
import sys
import pathlib
import platform
from dataclasses import dataclass

from modules.core.runtime import is_bundled_app, get_base_path
from modules.core.version import realbot_name, realbot_version

OS_NAME = platform.system()
gui = None


# If you're on Windows and just double-click this file, the terminal usually closes right away if things crash.
# That makes it hard to see what went wrong. So we'll wait for a key press before it shuts down.
def on_exit() -> None:
    if OS_NAME == "Windows":
        import psutil
        import os

        parent_process_name = psutil.Process(os.getppid()).name()
        if parent_process_name == "py.exe" or is_bundled_app():
            if gui is not None and gui.window is not None:
                gui.window.withdraw()

            input("\nPress Enter to close...")


atexit.register(on_exit)


@dataclass
class StartupSettings:
    profile: "Profile | None"
    debug: bool
    bot_mode: str
    headless: bool
    no_video: bool
    no_audio: bool
    no_theme: bool
    use_opengl: bool
    emulation_speed: int
    always_on_top: bool
    config_path: str


def directory_arg(value: str) -> pathlib.Path:
    """
    Checks if a string is a valid, readable directory.
    """
    path_obj = pathlib.Path(value)
    if not path_obj.is_dir() or not path_obj.exists():
        from modules.core import exceptions

        raise exceptions.CriticalDirectoryMissing(value)
    return path_obj


def parse_arguments(bot_mode_names: list[str]) -> StartupSettings:
    """
    Pulls settings from the command line.
    """
    parser = argparse.ArgumentParser(description=f"{realbot_name} {realbot_version}")
    parser.add_argument(
        "profile",
        nargs="?",
        help="Profile to initialize. Otherwise, the profile selection menu will appear.",
    )
    parser.add_argument("-m", "--bot-mode", choices=bot_mode_names, help="Initial bot mode (default: Manual).")
    parser.add_argument(
        "-s",
        "--emulation-speed",
        choices=["0", "1", "2", "3", "4", "8", "16", "32"],
        help="Initial emulation speed (0 for unthrottled; default: 1)",
    )
    parser.add_argument("-hl", "--headless", action="store_true", help="Run without a GUI, only using the console.")
    parser.add_argument("-nv", "--no-video", action="store_true", help="Turn off video output by default.")
    parser.add_argument("-na", "--no-audio", action="store_true", help="Turn off audio output by default.")
    parser.add_argument("-nt", "--no-theme", action="store_true", help="Turn off the fancy GUI theme.")
    parser.add_argument(
        "-gl", "--use-opengl", action="store_true", help="Use OpenGL to render the video output (potentially faster)"
    )
    parser.add_argument(
        "-t", "--always-on-top", action="store_true", help="Keep the bot window always on top of other windows."
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable extra debug options and a debug menu.")
    parser.add_argument("-c", "--config", type=directory_arg, dest="config_path", help=argparse.SUPPRESS)
    args = parser.parse_args()

    preselected_profile: Profile | None = None
    if args.profile and profile_directory_exists(args.profile):
        preselected_profile = load_profile_by_name(args.profile)

    return StartupSettings(
        profile=preselected_profile,
        debug=bool(args.debug),
        bot_mode=args.bot_mode or "Manual",
        headless=bool(args.headless),
        no_video=bool(args.no_video),
        no_audio=bool(args.no_audio),
        no_theme=bool(args.no_theme),
        use_opengl=bool(args.use_opengl),
        emulation_speed=int(args.emulation_speed or "1"),
        always_on_top=bool(args.always_on_top),
        config_path=args.config_path,
    )


if __name__ == "__main__":
    if not is_bundled_app():
        from requirements import check_requirements

        check_requirements()
    from modules.core.context import context
    from modules.core.console import console
    from modules.core.exceptions_hook import register_exception_hook
    from modules.core.main import main_loop
    from modules.modes import get_bot_mode_names
    from modules.core.plugins import load_plugins
    from modules.core.profiles import Profile, profile_directory_exists, load_profile_by_name
    from updater import run_updater

    register_exception_hook()
    load_plugins()

    # This catches when someone closes the console window on Windows.
    # We need to make sure the emulator saves everything before it's gone.
    if OS_NAME == "Windows":
        import win32api

        def win32_signal_handler(signal_type):
            if signal_type == 2 and context.emulator is not None:
                context.emulator.shutdown()

        win32api.SetConsoleCtrlHandler(win32_signal_handler, True)
    else:
        import signal

        def signal_handler(signum, frame):
            if context.emulator:
                context.emulator.shutdown()
            os._exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    startup_settings = parse_arguments(get_bot_mode_names())
    console.print(f"Starting [bold cyan]{realbot_name} {realbot_version}![/]")

    if not is_bundled_app() and not (get_base_path() / ".git").is_dir():
        run_updater()

    if startup_settings.headless:
        from modules.gui.headless import RealbotHeadless

        gui = RealbotHeadless(main_loop, on_exit)
    else:
        from modules.gui import RealbotGui

        # You used to only be able to turn off themes with an environment variable.
        # Now there's a command line flag for it, but we still support both to keep things simple.
        no_theme = os.getenv("REALBOT_UNTHEMED") == "1" or startup_settings.no_theme
        gui = RealbotGui(main_loop, on_exit, no_theme=no_theme, use_opengl=startup_settings.use_opengl)
    context.gui = gui

    gui.run(startup_settings)
