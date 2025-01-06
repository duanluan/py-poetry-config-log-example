import os
from src.conf.config import loadConfigYml
from src.log.util import compressArchiveLog
from src.log.logging import Logging

config: dict = {}
log = None


def _setupConfig(configFilePath):
  global config

  config = loadConfigYml(configFilePath)
  if not config:
    raise Exception("config read failed")


def _setupLog(configFilePath):
  global config, log

  if not config:
    _setupConfig(configFilePath)
  try:
    logConfig = config.get('log')
    if logConfig:
      logFile = logConfig.get('file')
      if not os.path.exists(logConfig.get('path')):
        os.makedirs(logConfig.get('path'))
      logPath = logConfig.get('path')
      logLevel = logConfig.get('level')
      logFmt = logConfig.get('fmt')
      log = Logging(logPath + "/" + logFile + ".log", level=logLevel, fmt=logFmt)
  except Exception:
    raise Exception("log setup failed")


_setupLog('res/conf/config.yml')
compressArchiveLog(log, config.get('log').get('path'), config.get('log').get('compress-level'))
