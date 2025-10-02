import logging
import re
import sys
from logging import handlers
import os

# Attempt to import py7zr. Compression functionality will be disabled if the import fails.
try:
    import py7zr
except ImportError:
    py7zr = None

# A mapping of log level names to their logging constants.
_levelRelations = {
  'notset': logging.NOTSET,
  'debug': logging.DEBUG,
  'info': logging.INFO,
  'warn': logging.WARN,
  'warning': logging.WARNING,
  'error': logging.ERROR,
  'fatal': logging.FATAL,
  'critical': logging.CRITICAL
}


class ArchivingTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    A custom TimedRotatingFileHandler that automatically performs compression and cleanup during log rotation.

    - Compresses rotated .log files that haven't been archived yet.
    - Retains a specified number of the most recent .log files based on backupCount.
    - Retains a specified number of the most recent compressed files based on compress_backup_count.
    """
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None, compress_suffix='.7z', compress_backup_count=0):
        """
        Initializes the handler.
        :param compress_suffix: The suffix for compressed files.
        :param compress_backup_count: The number of compressed files to keep (0 or negative means keep all).
        """
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        # Store the original backupCount for our custom log cleanup logic.
        self.real_backup_count = backupCount
        self.compress_suffix = compress_suffix
        # The number of compressed backups to retain.
        self.compress_backup_count = compress_backup_count

        # Infer the base name pattern from the log filename to match related files.
        base_filename = os.path.basename(filename)
        self.base_name_pattern = os.path.splitext(base_filename)[0]

        # Pre-compile regex for efficiency.
        # Matches filenames like 'app1_251003.log' or 'app1_251003_143000.log'.
        self.log_file_pattern = re.compile(rf"^{re.escape(self.base_name_pattern)}_\d{{6}}(_\d{{6}})?\.log$")
        # Matches corresponding archive filenames.
        self.archive_file_pattern = re.compile(rf"^{re.escape(self.base_name_pattern)}_\d{{6}}(_\d{{6}})?{re.escape(self.compress_suffix)}$")

    def doRollover(self):
        """
        Performs log rotation, followed by archiving and cleanup tasks.
        """
        # First, call the parent class's method to perform the standard log file rollover.
        super().doRollover()
        # Then, immediately execute our custom archival tasks.
        self._run_archival_tasks()

    def _get_sorted_files(self, pattern):
        """Finds and sorts files in the log directory based on a given regex pattern."""
        dir_path = os.path.dirname(self.baseFilename)
        try:
            # List all files in the directory, filter by the pattern, and sort them.
            files = [f for f in os.listdir(dir_path) if pattern.match(f)]
            files.sort()
            return files
        except OSError:
            return []

    def _run_archival_tasks(self):
        """Executes all archival tasks in sequence: compression, log cleanup, and archive cleanup."""
        # Get all rotated log files.
        all_log_files = self._get_sorted_files(self.log_file_pattern)
        if not all_log_files:
            return

        self._compress_new_logs(all_log_files)
        self._cleanup_old_logs(all_log_files)
        # Clean up old compressed archives.
        self._cleanup_old_archives()

    def _compress_new_logs(self, all_log_files):
        """Compresses any .log files that do not have a corresponding archive file."""
        if not py7zr:
            # Skip compression if the py7zr library is not installed.
            return

        dir_path = os.path.dirname(self.baseFilename)
        for log_filename in all_log_files:
            log_file_path = os.path.join(dir_path, log_filename)
            # Construct the corresponding archive filename.
            compress_file_path = os.path.splitext(log_file_path)[0] + self.compress_suffix

            if os.path.exists(compress_file_path):
                # Skip if the archive already exists.
                continue

            try:
                # Create the archive using py7zr.
                with py7zr.SevenZipFile(compress_file_path, 'w') as archive:
                    archive.write(log_file_path, arcname=os.path.basename(log_file_path))
            except Exception:
                # Silently skip on error to avoid interrupting the logging process.
                pass

    def _cleanup_old_logs(self, all_log_files):
        """Deletes the oldest .log files that exceed the backupCount limit."""
        if self.real_backup_count > 0 and len(all_log_files) > self.real_backup_count:
            dir_path = os.path.dirname(self.baseFilename)
            # Select the oldest files to delete from the sorted list.
            files_to_delete = all_log_files[:-self.real_backup_count]
            for filename in files_to_delete:
                try:
                    os.remove(os.path.join(dir_path, filename))
                except OSError:
                    pass

    def _cleanup_old_archives(self):
        """Deletes the oldest compressed files that exceed the compress_backup_count limit."""
        # If compress_backup_count is non-positive, do nothing (keep all archives).
        if self.compress_backup_count <= 0:
            return

        all_archive_files = self._get_sorted_files(self.archive_file_pattern)

        # Check if the number of archives exceeds the limit.
        if len(all_archive_files) > self.compress_backup_count:
            dir_path = os.path.dirname(self.baseFilename)
            archives_to_delete = all_archive_files[:-self.compress_backup_count]
            for filename in archives_to_delete:
                try:
                    os.remove(os.path.join(dir_path, filename))
                except OSError:
                    pass


def _namer(name):
  """
  Custom namer for log rotation to meet the "app1_YYMMDD_HHMMSS.log" format.
  """
  match = re.search(r'(.*)\.log\.(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$', name)
  if match:
    base_part = os.path.basename(match.group(1))
    date_part = match.group(2).replace('-', '')[2:]
    time_part = match.group(3).replace('-', '')
    dir_part = os.path.dirname(name)
    return os.path.join(dir_part, f"{base_part}_{date_part}_{time_part}.log")

  match_daily = re.search(r'(.*)\.log\.(\d{4}-\d{2}-\d{2})$', name)
  if match_daily:
    base_part = os.path.basename(match_daily.group(1))
    date_part = match_daily.group(2).replace('-', '')[2:]
    dir_part = os.path.dirname(name)
    return os.path.join(dir_part, f"{base_part}_{date_part}.log")

  return name


def create_logger(logger_name, log_file_path='app.log', level='info', when='midnight', bak_count=30, fmt='%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s', compress_suffix='.7z', compress_bak_count=90):
  """
  Factory function to create and configure a logger instance.
  """
  logger = logging.getLogger(logger_name)

  if logger.hasHandlers():
    return logger

  level = level.lower() if isinstance(level, str) else 'info'
  valid_level = _levelRelations.get(level, logging.INFO)
  logger.setLevel(valid_level)

  log_formatter = logging.Formatter(fmt)

  stream_handler = logging.StreamHandler(sys.stdout)
  stream_handler.setFormatter(log_formatter)
  logger.addHandler(stream_handler)

  # Use our full-featured ArchivingTimedRotatingFileHandler.
  file_handler = ArchivingTimedRotatingFileHandler(
    filename=log_file_path,
    when=when,
    backupCount=bak_count,
    encoding='utf-8',
    compress_suffix=compress_suffix,
    # Pass the parameter for compressed backup count.
    compress_backup_count=compress_bak_count
  )
  file_handler.setFormatter(log_formatter)
  file_handler.namer = _namer
  logger.addHandler(file_handler)

  return logger
