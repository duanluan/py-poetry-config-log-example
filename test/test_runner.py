import os
import time

from common import app_context

TEST_CONFIG_PATH = '../test/config-test.yml'

def run_test(duration_seconds: int):
  """
  Initializes the application with a test config and runs it for a specific duration.
  """
  print(f"--- Starting test with config '{TEST_CONFIG_PATH}' for {duration_seconds} seconds. ---")

  # Initialize the context, which will automatically call the modified create_logger.
  app_context.init(TEST_CONFIG_PATH, "app1_test")
  app_context.log.info(app_context.config)

  # Ensure the log directory exists.
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
      # Maintain a 0.5-second logging interval to clearly observe the effect within a 1-second rotation period.
      time.sleep(0.5)
  except KeyboardInterrupt:
    print("\nTest interrupted by user.")
  except Exception as e:
    app_context.log.exception('An error occurred during the test run.')
  finally:
    print("--- Test run finished. ---")


if __name__ == '__main__':
  # Running a 10-second test is sufficient to observe multiple rotations, compressions, and cleanups.
  print(">>> Running Integrated Log Rotation, Compression, and Cleanup Test (10 seconds)...")
  run_test(10)
