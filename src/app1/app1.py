import time

# Import the application context and the log archiver module.
# 导入应用上下文和日志归档模块。
from common import app_context

def main():
  # Initialize the app context, loading config and setting up the logger.
  # 初始化应用上下文，加载配置并设置日志记录器。
  app_context.init('app1/res/config.yml', "app1")

  try:
    # Log the AppSettings instance for the config.
    # 记录配置文件对应的 AppSettings 实例。
    app_context.log.info(app_context.config)

    # Main loop to keep the application running for background tasks.
    # 主循环使应用保持运行以执行后台任务。
    count = 0
    while True:
      count += 1
      app_context.log.info(f"This is a continuous log message, count: {count}")
      # 0.5-second interval, as logs will be split at least every second
      # 0.5 秒间隔，因为日志最短会每秒拆分一次
      time.sleep(0.5)
  except Exception:
    # Log any unexpected exceptions in the main loop.
    # 记录主循环中的任何意外异常。
    app_context.log.exception('An unexpected error occurred in the main loop.')


if __name__ == '__main__':
  main()
