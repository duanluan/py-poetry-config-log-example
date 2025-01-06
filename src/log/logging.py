import logging
import re
import sys
from logging import handlers


class Logging(object):
  # log level relationship mapping
  levelRelations = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
  }

  def namer(self, name):
    """
    When performing logging rotation, the new filename will be in the format:
    original_filename.%Y-%m-%d. This method replaces it with
    original_filename(without extension)_%Y-%m-%d.log
    """
    return re.search(r'(.*).log.\d{4}-\d{2}-\d{2}', name).group(1) + "_" + re.search(r'(\d{4}-\d{2}-\d{2})$', name).group(1) + ".log"

  def __init__(self, logFilePath='app.log', level='info', when='midnight', bakCount=30, fmt='%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s'):
    """
    Initialize the logger.
    :param logFilePath: Path to the log file
    :param level: Logging level: critical > error > warning > info > debug > notset
    :param when: Log rotation interval: S: seconds, M: minutes, H: hours, D: days, W0~W6: day of the week, midnight: daily at midnight
    :param bakCount: Number of log files to retain
    :param fmt: Log message format
    """
    level = level if level in ('debug', 'info', 'warning', 'error', 'critical') else 'info'
    fmt = fmt if fmt else '%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s'

    self.logger = logging.getLogger(logFilePath)
    # Check if a logger handler has already been created
    if not self.logger.handlers:
      self.logger.setLevel(self.levelRelations.get(level))
      logFormatter = logging.Formatter(fmt)

      # Stream handler to output logs to the console
      streamHandler = logging.StreamHandler()
      streamHandler.setFormatter(logFormatter)
      self.logger.addHandler(streamHandler)
      # Flush the standard output buffer to ensure previous log messages are immediately displayed on the console
      sys.stdout.flush()

      # Timed rotating file handler to append logs to a file
      fileHandler = handlers.TimedRotatingFileHandler(filename=logFilePath, when=when, backupCount=bakCount, encoding='utf-8')
      # Append mode
      fileHandler.mode = 'a'
      fileHandler.setFormatter(logFormatter)
      # Custom file naming for rotation
      fileHandler.namer = self.namer
      self.logger.addHandler(fileHandler)

  def __getattr__(self, name):
    # When log.xxx is called, if the method name matches a logging level, return the corresponding logging method
    if name in self.levelRelations:
      return getattr(self.logger, name)
    # Return the value of the specified attribute of the logger object
    return self.logger.__getattribute__(name)
