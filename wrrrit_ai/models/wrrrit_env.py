import os
import logging
from odoo.tools import config


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
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevents log propagation to higher level loggers

ch = logging.StreamHandler()
ch.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))
logger.addHandler(ch)


class EnvLoader:
    def __init__(self):
        self.logger = logger

    def load_env(self):
        # Retrieve the .env file path from the Odoo configuration
        env_file_path = config.get("odoo_env")

        # If env_file_path is set and file exists, load it
        if env_file_path and os.path.exists(env_file_path):
            from dotenv import load_dotenv

            load_dotenv(env_file_path)
            self.logger.envinfo(f"Loaded environment variables from: ## {env_file_path}.")
            self._log_loaded_envs(env_file_path)
        else:
            # Informing that default system environment variables are being used
            self.logger.info(
                "Using default system environment variables; no .env file loaded."
            )

    def _log_loaded_envs(self, env_file_path):
        self.logger.envinfo("Environment variables loaded from Env file: %s", env_file_path)
        with open(env_file_path, "r") as file:
            lines = file.readlines()
            env_vars = {}
            for line in lines:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value

            for key in sorted(env_vars.keys()):
                self.logger.envinfo(f"{key}: {env_vars[key]}")
