import argparse
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, ValidationError, field_validator

import yaml


class LogSettings(BaseSettings):
  """
  Represents the logging configuration settings for the application.
  表示应用程序的日志配置设置
  """
  path: str = "./logs"
  file: str = "app"
  level: str = "info"
  fmt: str = "%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s"
  when: str = "midnight"
  # Use an alias to allow kebab-case in the YAML file (e.g., 'bak-count').
  # 使用别名以允许在 YAML 文件中使用 kebab-case (例如, 'bak-count')。
  bak_count: int = Field(alias="bak-count", default=30, ge=0)
  compress_level: int = Field(alias="compress-level", default=9, ge=0, le=9)
  compress_suffix: str = Field(alias="compress-suffix", default=".7z")
  compress_schedule_cron: str = Field(alias="compress-schedule-cron", default="0 1 * * *")
  # Archive retention count. If smaller than bak_count, effective retention is raised to bak_count to avoid repeated recompression.
  # 压缩归档保留数量。若小于 bak_count，为避免重复压缩，实际保留数会提升到 bak_count。
  compress_bak_count: int = Field(alias="compress-bak-count", default=90, ge=0)

  @field_validator('compress_suffix', mode='before')
  @classmethod
  def normalize_compress_suffix(cls, value):
    """
    Accept both 'zip' and '.zip' styles, normalize to '.zip' / '.7z'.
    同时接受 'zip' 和 '.zip' 写法，统一规范为 '.zip' / '.7z'。
    """
    if value is None:
      return '.7z'
    if not isinstance(value, str):
      raise TypeError(f"compress-suffix must be a string, got {type(value).__name__}")

    suffix = value.strip().lower()
    if not suffix:
      return '.7z'
    if not suffix.startswith('.'):
      suffix = f'.{suffix}'
    return suffix

  @field_validator('compress_schedule_cron', mode='before')
  @classmethod
  def normalize_compress_schedule_cron(cls, value):
    """
    Normalize cron string and keep empty value as "disabled scheduler".
    规范化 cron 字符串，并保留空值用于“禁用定时压缩”。
    """
    if value is None:
      return ''
    if not isinstance(value, str):
      raise TypeError(
        f"compress-schedule-cron must be a string, got {type(value).__name__}"
      )
    return value.strip()


class AppSettings(BaseSettings):
  """
  Defines the main application settings, aggregating other settings models.
  定义主应用程序设置，聚合其他设置模型。
  """
  # By setting model_config, we allow extra fields that are not explicitly defined in the model. This enables loading of any top-level keys from the config.yml file, such as 'log' and other custom sections (e.g., 'database').
  # 通过设置 model_config，我们允许模型中未明确定义的额外字段。这使得可以从 config.yml 文件加载任何顶级键，例如 'log' 和其他自定义部分 (例如, 'database')。
  model_config = ConfigDict(extra='allow')

  # Use default_factory to avoid shared mutable defaults in model field definitions.
  # 使用 default_factory 避免模型字段默认值的共享实例问题。
  log: LogSettings = Field(default_factory=LogSettings)


def find_project_root(marker_file: str = 'pyproject.toml') -> Path:
  """
  Searches upwards from the current file's directory to find the project root.
  从当前文件所在目录向上搜索以查找项目根目录。
  :param marker_file: The name of the file to look for to identify the root. Defaults to 'pyproject.toml'. 用于识别根目录的文件名。默认为 'pyproject.toml'。
  :return: A Path object representing the project's root directory. 代表项目根目录的 Path 对象。
  :raises FileNotFoundError: If the project root cannot be determined by traversing up from the current file path. 如果从当前文件路径向上遍历无法确定项目根目录。
  """
  current_path = Path(__file__).resolve()
  # The loop should terminate when we reach the filesystem root, where  current_path.parent is the same as current_path.
  # 当我们到达文件系统根目录时，循环应该终止，此时 current_path.parent 与 current_path 相同。
  while current_path.parent != current_path:
    if (current_path / marker_file).is_file():
      return current_path
    current_path = current_path.parent
  # A final check in case the script is run from the project root itself.
  # 最后检查一下，以防脚本本身就是从项目根目录运行的。
  if (current_path / marker_file).is_file():
    return current_path
  raise FileNotFoundError(f"Project root with '{marker_file}' not found.")


def load_config_yml(config_file_rel_path: str) -> AppSettings:
  """
  Loads a YAML configuration file and parses it into an AppSettings object. The path to the configuration file can be specified via the '--config' command-line argument. If it's not provided, a default path relative to the project's 'src' directory is used.
  加载 YAML 配置文件并将其解析为 AppSettings 对象。配置文件的路径可以通过 '--config' 命令行参数指定。如果没有提供该参数，则使用相对于项目 'src' 目录的默认路径。

  :param config_file_rel_path: The default relative path to the config file (from 'src' folder), used if the '--config' argument is not provided. 配置文件的默认相对路径 (从 'src' 文件夹算起)，在未提供 '--config' 参数时使用。
  :return: An AppSettings object populated with the loaded configuration. 一个填充了已加载配置的 AppSettings 对象。
  :raises FileNotFoundError: If the configuration file cannot be found at the determined path. 如果在确定的路径下找不到配置文件。
  :raises Exception: If there is an error reading or parsing the YAML file. 如果读取或解析 YAML 文件时出错。
  """
  # Parse command-line arguments to check for an explicit config file path.
  # 解析命令行参数以检查是否显式指定了配置文件路径。
  parser = argparse.ArgumentParser(description="Load application configuration.")
  parser.add_argument('--config', type=str, help='Absolute or relative path to the YAML config file.')
  args, _ = parser.parse_known_args()

  # Determine the absolute path of the configuration file.
  # 确定配置文件的绝对路径。
  if args.config:
    # Use the path provided via the --config command-line argument.
    # 使用通过 --config 命令行参数提供的路径。
    config_file_abs_path = Path(args.config).expanduser().resolve()
  else:
    # If not provided, construct the default path from the project root.
    # 如果未提供，则从项目根目录构建默认路径。
    # This assumes a project structure like: project_root/src/config.yml
    # 这里假设项目结构类似于：project_root/src/config.yml
    project_root = find_project_root()
    config_file_abs_path = project_root / 'src' / config_file_rel_path

  try:
    # Read and parse the YAML configuration file.
    # 读取并解析 YAML 配置文件。
    with open(config_file_abs_path, 'r', encoding='utf-8') as file_path:
      # Use yaml.safe_load for security against arbitrary code execution.
      # 使用 yaml.safe_load 以防止任意代码执行，增强安全性。
      full_config = yaml.safe_load(file_path)
      if full_config is None:
        full_config = {}
  except FileNotFoundError as e:
    raise FileNotFoundError(f"Configuration file not found at: {config_file_abs_path}") from e
  except yaml.YAMLError as e:
    raise ValueError(f"Invalid YAML syntax in: {config_file_abs_path}. {e}") from e
  except OSError as e:
    raise RuntimeError(f"Failed to read configuration file: {config_file_abs_path}. {e}") from e

  if not isinstance(full_config, dict):
    raise ValueError(
      f"Configuration root must be a mapping (YAML object), got: {type(full_config).__name__}."
    )

  try:
    return AppSettings.model_validate(full_config)
  except ValidationError as e:
    raise ValueError(f"Invalid configuration at {config_file_abs_path}: {e}") from e
