def setup_terminate_signal_if_win(close_callback=None):
    """Setup a signal handler for windows to catch Ctrl+C"""
    import sys

    is_windows = sys.platform.startswith("win")
    if not is_windows:
        return

    from engineio.client import signal_handler
    from win32api import SetConsoleCtrlHandler

    def handler(event):
        import inspect
        import signal

        if event == 0:
            try:
                if close_callback:
                    close_callback()
                signal_handler(signal.SIGINT, inspect.currentframe())
            except:
                # SetConsoleCtrlHandler handle cannot raise exceptions
                pass

    SetConsoleCtrlHandler(handler, 1)
