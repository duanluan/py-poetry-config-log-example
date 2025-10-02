import argparse
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

import yaml


class LogSettings(BaseSettings):
  """Represents the logging configuration settings for the application."""
  path: str = "./logs"
  file: str = "app"
  level: str = "info"
  fmt: str = "%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s"
  when: str = "midnight"
  # Use an alias to allow kebab-case in the YAML file (e.g., 'bak-count').
  bak_count: int = Field(alias="bak-count", default=30)
  compress_level: int = Field(alias="compress-level", default=9)
  compress_suffix: str = Field(alias="compress-suffix", default=".7z")
  compress_schedule_cron: str = Field(alias="compress-schedule-cron", default="0 1 * * *")
  compress_bak_count: int = Field(alias="compress-bak-count", default=90)


class AppSettings(BaseSettings):
  """
  Defines the main application settings, aggregating other settings models.
  """
  # By setting model_config, we allow extra fields that are not explicitly defined in the model. This enables loading of any top-level keys from the config.yml file, such as 'log' and other custom sections (e.g., 'database').
  model_config = ConfigDict(extra='allow')

  log: LogSettings = LogSettings()


def find_project_root(marker_file: str = 'pyproject.toml') -> Path:
  """
  Searches upwards from the current file's directory to find the project root.

  The project root is identified by the presence of a marker file.

  :param marker_file: The name of the file to look for to identify the root. Defaults to 'pyproject.toml'.
  :return: A Path object representing the project's root directory.
  :raises FileNotFoundError: If the project root cannot be determined by traversing up from the current file path.
  """
  current_path = Path(__file__).resolve()
  # The loop should terminate when we reach the filesystem root, where
  # current_path.parent is the same as current_path.
  while current_path.parent != current_path:
    if (current_path / marker_file).is_file():
      return current_path
    current_path = current_path.parent
  # A final check in case the script is run from the project root itself.
  if (current_path / marker_file).is_file():
    return current_path
  raise FileNotFoundError(f"Project root with '{marker_file}' not found.")


def load_config_yml(config_file_rel_path: str) -> AppSettings:
  """
  Loads a YAML configuration file and parses it into an AppSettings object.

  The path to the configuration file can be specified via the '--config' command-line argument. If it's not provided, a default path relative to the project's 'src' directory is used.

  :param config_file_rel_path: The default relative path to the config file (from 'src' folder), used if the '--config' argument is not provided.
  :return: An AppSettings object populated with the loaded configuration.
  :raises FileNotFoundError: If the configuration file cannot be found at the determined path.
  :raises Exception: If there is an error reading or parsing the YAML file.
  """
  # Parse command-line arguments to check for an explicit config file path.
  parser = argparse.ArgumentParser(description="Load application configuration.")
  parser.add_argument('--config', type=str, help='Absolute or relative path to the YAML config file.')
  args, _ = parser.parse_known_args()

  # Determine the absolute path of the configuration file.
  if args.config:
    # Use the path provided via the --config command-line argument.
    config_file_abs_path = Path(args.config).resolve()
  else:
    # If not provided, construct the default path from the project root.
    # This assumes a project structure like: project_root/src/config.yml
    project_root = find_project_root()
    config_file_abs_path = project_root / 'src' / config_file_rel_path

  try:
    # Read and parse the YAML configuration file.
    with open(config_file_abs_path, 'r', encoding='utf-8') as file_path:
      # Use yaml.safe_load for security against arbitrary code execution.
      full_config = yaml.safe_load(file_path)
      if full_config is None:
        full_config = {}
  except FileNotFoundError:
    raise FileNotFoundError(f"Configuration file not found at: {config_file_abs_path}")
  except Exception as e:
    raise Exception(f"Failed to read or parse the configuration file at {config_file_abs_path}: {e}")

  return AppSettings(**full_config)
