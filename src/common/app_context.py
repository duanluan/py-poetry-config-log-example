import logging
import os
from logging import Logger

from common.conf.config import load_config_yml, LogSettings, AppSettings
from common.log.logger_factory import create_logger

# Global application settings, initialized with default values.
# This will be replaced by the loaded configuration in the init() function.
config: AppSettings = AppSettings()

# Global logger instance. It is initialized with a NullHandler by default.
# This prevents "No handler found" warnings if a module uses the logger before
# the init() function has been called.
log: Logger = logging.getLogger('null')
log.addHandler(logging.NullHandler())


def init(config_file_path: str, logger_name: str):
  """
  Initializes the application context by loading the configuration and setting up the logger.
  This function should be called once at the start of the application.

  :param config_file_path: The path to the configuration file.
  :param logger_name: The name to assign to the logger instance.
  :raises ValueError: If the configuration file fails to load.
  :raises KeyError: If a required logging setting is missing from the configuration.
  :raises RuntimeError: If the logger setup fails for any other reason.
  """
  global config, log

  # Load configuration from the specified YAML file.
  config = load_config_yml(config_file_path)
  if not config:
    raise ValueError("Failed to load configuration.")

  # Set up the logger based on the loaded configuration.
  try:
    log_settings: LogSettings = config.log
    log_path = log_settings.path

    # Ensure the log directory exists.
    os.makedirs(log_path, exist_ok=True)
    full_log_path = os.path.join(log_path, f"{log_settings.file}.log")

    # Use the factory function to create the logger and overwrite the global instance.
    log = create_logger(
      logger_name=logger_name,
      log_file_path=full_log_path,
      level=log_settings.level,
      fmt=log_settings.fmt,
      when=log_settings.when,
      bak_count=log_settings.bak_count,
      compress_bak_count=log_settings.compress_bak_count
    )
  except KeyError as e:
    raise KeyError(f"A required logging configuration key is missing: {e}")
  except Exception as e:
    raise RuntimeError(f"Failed to set up the logging system: {e}")
