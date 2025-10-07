import logging
import os
from logging import Logger

from common.conf.config import load_config_yml, LogSettings, AppSettings
from common.log.logger_factory import create_logger

# Global application settings, initialized with default values.
# 全局应用程序设置，使用默认值进行初始化。
# This will be replaced by the loaded configuration in the init() function.
# 在 init() 函数中，它将被加载的配置所替换。
config: AppSettings = AppSettings()

# Global logger instance. It is initialized with a NullHandler by default.
# This prevents "No handler found" warnings if a module uses the logger before
# 全局日志记录器实例。默认情况下，它使用一个 NullHandler 进行初始化。
# the init() function has been called.
# 这可以防止在 init() 函数被调用之前，如果某个模块使用了该记录器，会出现 "No handler found" 的警告。
log: Logger = logging.getLogger('null')
log.addHandler(logging.NullHandler())


def init(config_file_path: str, logger_name: str):
  """
  Initializes the application context by loading the configuration and setting up the logger.
  通过加载配置和设置日志记录器来初始化应用程序上下文。
  This function should be called once at the start of the application.
  该函数应在应用程序启动时调用一次。

  :param config_file_path: The path to the configuration file. 配置文件的路径。
  :param logger_name: The name to assign to the logger instance. 要分配给日志记录器实例的名称。
  :raises ValueError: If the configuration file fails to load. 如果配置文件加载失败。
  :raises KeyError: If a required logging setting is missing from the configuration. 如果配置中缺少必需的日志设置。
  :raises RuntimeError: If the logger setup fails for any other reason. 如果日志系统因任何其他原因设置失败。
  """
  global config, log

  # Load configuration from the specified YAML file.
  # 从指定的 YAML 文件加载配置。
  config = load_config_yml(config_file_path)
  if not config:
    raise ValueError("Failed to load configuration.")

  # Set up the logger based on the loaded configuration.
  # 根据加载的配置设置日志记录器。
  try:
    log_settings: LogSettings = config.log
    log_path = log_settings.path

    # Ensure the log directory exists.
    # 确保日志目录存在。
    os.makedirs(log_path, exist_ok=True)
    full_log_path = os.path.join(log_path, f"{log_settings.file}.log")

    # Use the factory function to create the logger and overwrite the global instance.
    # 使用工厂函数创建日志记录器并覆盖全局实例。
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
