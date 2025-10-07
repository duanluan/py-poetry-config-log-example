import time

# Import the application context and the log archiver module.
from common import app_context

def main():
  # Initialize the application context. This loads the configuration from a file and sets up the global logger instance.
  app_context.init('app1/res/config.yml', "app1")

  try:
    # Log the loaded configuration for debugging or verification purposes.
    app_context.log.info(app_context.config)

    # Main loop to keep the application running, allowing background tasks (like the archiver) to execute.
    while True:
      time.sleep(1)
  except Exception:
    # Log any unexpected exceptions that occur during the main loop.
    app_context.log.exception('An unexpected error occurred in the main loop.')


if __name__ == '__main__':
  main()
