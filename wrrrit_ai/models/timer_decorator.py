import time
import logging

ENABLE_TIMER = True  # Set this variable to True or False in your calling scope

# Create a logger
logger = logging.getLogger(__name__)


def log_execution_time(enable_timer=True):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if enable_timer:
                start_time = time.time()
                logger.info(f"Entering {func.__name__}")
                result = func(*args, **kwargs)
                end_time = time.time()
                logger.info(f"Exiting {func.__name__}")
                logger.info(
                    f"{func.__name__} took {end_time - start_time} seconds to execute."
                )
            else:
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


# Usage of the decorator with ENABLE_TIMER
