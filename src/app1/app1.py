import time

from common import app_context
from common.app_context import log, config


def main():
  # Initialize the app context, loading config and setting up the logger.
  # 初始化应用上下文，加载配置并设置日志记录器。
  app_context.init('app1/res/config.yml', "app1")

  try:
    # Log the AppSettings instance for the config.
    # 记录配置文件对应的 AppSettings 实例。
    log.info(config)

    # Main loop to keep the application running for background tasks.
    # 主循环使应用保持运行以执行后台任务。
    count = 0
    while True:
      count += 1
      log.info(f"This is a continuous log message, count: {count}")
      # 0.5-second interval, as logs will be split at least every second
      # 0.5 秒间隔，因为日志最短会每秒拆分一次
      time.sleep(0.5)
  except Exception:
    # Log any unexpected exceptions in the main loop.
    # 记录主循环中的任何意外异常。
    log.exception('An unexpected error occurred in the main loop.')


if __name__ == '__main__':
  main()
