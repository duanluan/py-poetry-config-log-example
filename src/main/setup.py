import time

from src.main.core import config, log


def main():
  log.info(config)
  while True:
    time.sleep(1)


if __name__ == '__main__':
  main()
