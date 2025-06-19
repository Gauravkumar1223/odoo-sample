import logging


# Define ANSI escape sequences for colors
class ANSIColors:
    YELLOW = "\033[93m"
    RESET = "\033[0m"


# Custom log level
logging.ENVINFO = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(logging.ENVINFO, "ENVINFO")


def envinfo(self, message, *args, **kws):
    if self.isEnabledFor(logging.ENVINFO):
        self._log(logging.ENVINFO, message, args, **kws)


# Add the envinfo method to logging.Logger
logging.Logger.envinfo = envinfo


class ColorFormatter(logging.Formatter):
    """Custom formatter to add color to ENVINFO logging output"""

    def format(self, record):
        if record.levelno == logging.ENVINFO:
            return f"{ANSIColors.YELLOW}{super().format(record)}{ANSIColors.RESET}"
        else:
            return super().format(record)


# Set up logger with custom formatter
logger = logging.getLogger("my_custom_logger")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))
logger.addHandler(ch)

# Test the custom log level and formatter
logger.envinfo("This is an ENVINFO message.")
logger.info("This is a regular INFO message.")
