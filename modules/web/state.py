# Copyright (c) 2026 realgarit
from modules.console import console
from modules.main import work_queue
from modules.state_cache import StateCacheItem

custom_state: dict = {}


def _update_via_work_queue(
    state_cache_entry: StateCacheItem, update_callback: callable, maximum_age_in_frames: int = 5
) -> None:
    """
    Ensures that an entry in the State cache is up-to-date.

    If not, it executes an update call in the main thread's work queue and will
    suppress any errors that occur.

    The reason we use a work queue is that the HTTP server runs in a separate thread
    and so is not synchronous with the emulator core. So if it were to read emulator
    memory, it might potentially get incomplete/garbage data.

    The work queue is just a list of callbacks that the main thread will execute
    after the current frame is emulated.

    Because these data-updating callbacks might fail anyway (due to the game being in
    a weird state or something like that), this function will just ignore these errors
    and pretend that the data has been updated.

    This means that the HTTP API will potentially return some outdated data, but it's
    just a reporting tool anyway.

    :param state_cache_entry: The state cache item that needs to be up-to-date.
    :param update_callback: A callback that will update the data in the state cache.
    :param maximum_age_in_frames: Defines how many frames old the data may be to still
                                  be considered up-to-date. If the data is 'younger'
                                  than or equal to that number of frames, this function
                                  will do nothing.
    """
    if state_cache_entry.age_in_frames < maximum_age_in_frames:
        return

    def do_update():
        try:
            update_callback()
        except Exception:
            # We don't want to spam the console with errors if the game is in a weird state
            # console.print_exception()
            pass

    try:
        work_queue.put_nowait(do_update)
        work_queue.join()
    except Exception:
        console.print_exception()
        return
