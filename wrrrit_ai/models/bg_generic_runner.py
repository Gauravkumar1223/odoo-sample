import threading
import functools
import logging
import traceback

_logger = logging.getLogger(__name__)


def run_in_background(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        action_name = func.__name__.replace("_", " ").capitalize()
        _logger.info(f"Running background action: {action_name}")

        def run():
            try:
                _logger.info(f"Starting background action: {action_name}")
                result = func(*args, **kwargs)
                _logger.info(f"Background action completed successfully: {result}")
            except Exception as e:
                _logger.error(f"Exception in background thread: {e}")
                _logger.error(traceback.format_exc())

        thread = threading.Thread(target=run, args=())
        thread.daemon = True  # Set the thread as a daemon thread
        thread.start()

    return wrapper
