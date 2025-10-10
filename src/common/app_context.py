import os
from logging import Logger

from common.conf.config import load_config_yml, LogSettings, AppSettings
from common.log.logger_factory import create_logger


# 定义一个通用的上下文代理类
# Define a generic context proxy class
class ContextProxy:
  """
  A proxy for a context object that will be initialized later. This allows modules to import the proxy instance (`log`, `config`) directly, and it will automatically forward calls to the real object once `init()` is called.
  一个上下文对象的代理，该对象将在稍后被初始化。这允许模块直接导入代理实例（`log`、`config`），并在 `init()` 被调用后，它会自动将调用转发给真实的对象。
  """
  _instance = None

  def set_instance(self, instance):
    """
    Called by the init function to inject the real, configured object.
    由 init 函数调用，以注入真实的、已配置的对象。
    """
    self._instance = instance

  def __getattr__(self, name):
    """
    Magic method that intercepts attribute access (e.g., `log.info`).
    拦截属性访问的魔法方法（例如 `log.info`）。
    It forwards the access to the real instance.
    它将访问请求转发给真实的实例。
    """
    if self._instance is None:
      # This error will be raised if you try to use log or config before calling init().
      # 如果您在调用 init() 之前尝试使用 log 或 config，将会引发此错误。
      raise RuntimeError("The application context has not been initialized. Please call 'init()' first.")
    return getattr(self._instance, name)


# 使用代理类的实例作为全局变量
# Use instances of the proxy class as global variables
config: AppSettings = ContextProxy()
log: Logger = ContextProxy()


def init(config_file_path: str, logger_name: str):
  """
  This function now injects the created objects into the proxy instances.
  该函数现在将创建的对象注入到代理实例中。

  :param config_file_path: The path to the configuration file. 配置文件的路径。
  :param logger_name: The name to assign to the logger instance. 要分配给日志记录器实例的名称。
  :raises ValueError: If the configuration file fails to load. 如果配置文件加载失败。
  :raises KeyError: If a required logging setting is missing from the configuration. 如果配置中缺少必需的日志设置。
  :raises RuntimeError: If the logger setup fails for any other reason. 如果日志系统因任何其他原因设置失败。
  """

  # Load configuration from the specified YAML file.
  # 从指定的 YAML 文件加载配置。
  loaded_config = load_config_yml(config_file_path)
  if not loaded_config:
    raise ValueError("Failed to load configuration.")

  # Inject the loaded config into the config proxy.
  # 将加载的配置注入到 config 代理中。
  config.set_instance(loaded_config)

  # Set up the logger based on the loaded configuration.
  # 根据加载的配置设置日志记录器。
  try:
    log_settings: LogSettings = loaded_config.log
    log_path = log_settings.path

    # Ensure the log directory exists.
    # 确保日志目录存在。
    os.makedirs(log_path, exist_ok=True)
    full_log_path = os.path.join(log_path, f"{log_settings.file}.log")

    # Create the real logger instance.
    # 创建真实的日志记录器实例。
    created_logger = create_logger(
      logger_name=logger_name,
      log_file_path=full_log_path,
      level=log_settings.level,
      fmt=log_settings.fmt,
      when=log_settings.when,
      bak_count=log_settings.bak_count,
      compress_bak_count=log_settings.compress_bak_count
    )
    # Inject the created logger into the log proxy.
    # 将创建的日志记录器注入到 log 代理中。
    log.set_instance(created_logger)
  except KeyError as e:
    raise KeyError(f"A required logging configuration key is missing: {e}")
  except Exception as e:
    raise RuntimeError(f"Failed to set up the logging system: {e}")
