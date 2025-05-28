import time

from src.main.core import config, log


def main():
  try:
    log.info(config)
    while True:
      time.sleep(1)
  except Exception:
    log.exception('program exception')


if __name__ == '__main__':
  main()
