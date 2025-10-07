import os
import time

from common import app_context

TEST_CONFIG_PATH = '../test/config-test.yml'

def run_test(duration_seconds: int):
  """
  Initializes the application with a test config and runs it for a specific duration.
  使用测试配置初始化应用程序，并运行指定的持续时间。
  """
  print(f"--- Starting test with config '{TEST_CONFIG_PATH}' for {duration_seconds} seconds. ---")

  # Log the AppSettings instance for the config.
  # 记录配置文件对应的 AppSettings 实例。
  app_context.init(TEST_CONFIG_PATH, "app1_test")

  app_context.log.info(app_context.config)

  # Ensure the log directory exists.
  # 确保日志目录存在。
  log_dir = app_context.config.log.path
  if not os.path.exists(log_dir):
    os.makedirs(log_dir)

  try:
    print(f"--- Generating log messages... Check the '{log_dir}' directory. ---")
    print("--- Log files will be rotated, compressed, and cleaned up in real-time. ---")
    start_time = time.time()
    count = 0
    while time.time() - start_time < duration_seconds:
      count += 1
      app_context.log.info(f"This is a test log message, count: {count}")
      # 0.5-second interval, as logs will be split at least every second
      # 0.5 秒间隔，因为日志最短会每秒拆分一次
      time.sleep(0.5)
  except KeyboardInterrupt:
    print("\nTest interrupted by user.")
  except Exception as e:
    app_context.log.exception('An error occurred during the test run.')
  finally:
    print("--- Test run finished. ---")


if __name__ == '__main__':
  # Running a 10-second test is sufficient to observe multiple rotations, compressions, and cleanups.
  # 运行 10 秒的测试足以观察到多次轮替、压缩和清理。
  print(">>> Running Integrated Log Rotation, Compression, and Cleanup Test (10 seconds)...")
  run_test(10)