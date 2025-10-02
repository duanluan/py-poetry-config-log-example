import os
import re
import threading
from logging import handlers  # Import handlers for type checking.

from apscheduler.schedulers.background import BackgroundScheduler

from common.conf.config import AppSettings


class LogArchiver:
  """
  A class to handle scheduled compression and cleanup of log files.

  - Compresses all rotated .log files that have not yet been compressed.
  - Retains a specified number of the most recent .log files based on 'bak-count'.
  - Retains a specified number of the most recent compressed archives based on 'bak-count'.
  """

  def __init__(self, log, log_file_path, log_compress_level, log_compress_suffix, compress_schedule_cron, bak_count):
    """
    Initializes the LogArchiver.
    :param log: Logger instance for logging messages.
    :param log_file_path: Path to the log file directory.
    :param log_compress_level: Compression level (0-9 for 7z).
    :param log_compress_suffix: File extension for compressed files (e.g., '.7z', '.zip').
    :param compress_schedule_cron: Cron expression for the archival schedule.
    :param bak_count: The number of recent .log files AND archives to keep.
    """
    self.log = log
    self.log_file_path = log_file_path
    self.log_compress_level = log_compress_level
    self.log_compress_suffix = log_compress_suffix
    self.log_compress_schedule_cron = compress_schedule_cron
    self.bak_count = bak_count
    self.scheduler = BackgroundScheduler()

    # Robustly gets the base filename directly from the logger's file handler.
    base_name_pattern = None
    for handler in self.log.handlers:
      if isinstance(handler, handlers.TimedRotatingFileHandler):
        # handler.baseFilename is the full path, e.g., 'logs/app1.log'
        filename = os.path.basename(handler.baseFilename)  # e.g., 'app1.log'
        base_name_pattern = filename.replace('.log', '')  # e.g., 'app1'
        break

    if not base_name_pattern:
      # Fallback to a name-based pattern if the handler isn't found.
      self.log.warning("Could not find TimedRotatingFileHandler on the logger. Falling back to name-based pattern.")
      base_name_pattern = self.log.name.split('_')[0]

    self.log.info(f"LogArchiver initialized with base name pattern: '{base_name_pattern}'")

    # Pre-compile regex for efficiency.
    self.log_file_pattern = re.compile(rf"^{base_name_pattern}_\d{{6}}(_\d{{6}})?\.log$")
    self.archive_file_pattern = re.compile(rf"^{base_name_pattern}_\d{{6}}(_\d{{6}})?{re.escape(self.log_compress_suffix)}$")

  @classmethod
  def from_config(cls, log, config: AppSettings):
    """
    Factory method to create a LogArchiver instance from a configuration object.
    """
    try:
      log_config = config.log
      return cls(log, log_config.path, log_config.compress_level, log_config.compress_suffix, log_config.compress_schedule_cron, log_config.bak_count)
    except (KeyError, AttributeError) as e:
      log.error(f"Failed to create LogArchiver. A configuration key may be missing: {e}")
      raise

  def _run_archival_tasks(self):
    """A wrapper function that runs all archival tasks in sequence."""
    self.log.info("--- Starting scheduled log archival job ---")
    if not os.path.exists(self.log_file_path):
      self.log.warning(f"Log directory not found: {self.log_file_path}. Job will be skipped.")
      return

    all_log_files = self._get_sorted_files(self.log_file_pattern)

    # If no matching files are found, log the event and stop.
    if not all_log_files:
      self.log.info("No matching log files found to process.")
      self.log.info("--- Log archival job finished ---")
      return

    self._compress_new_logs(all_log_files)
    self._cleanup_old_logs(all_log_files)
    self._cleanup_old_archives()
    self.log.info("--- Log archival job finished ---")

  def _get_sorted_files(self, pattern):
    """Finds and sorts files in the log directory based on a regex pattern."""
    try:
      files = [f for f in os.listdir(self.log_file_path) if pattern.match(f)]
      files.sort()
      return files
    except Exception as e:
      self.log.error(f"Failed to read and sort files from log directory {self.log_file_path}: {e}")
      return []

  def _compress_new_logs(self, all_log_files):
    """Compresses all .log files that do not have a corresponding archive."""
    self.log.info("Step 1: Checking for new logs to compress...")
    compressed_count = 0
    for log_filename in all_log_files:
      log_file_path = os.path.join(self.log_file_path, log_filename)
      compress_file_path = os.path.splitext(log_file_path)[0] + self.log_compress_suffix

      if os.path.exists(compress_file_path):
        # Archive already exists, skip.
        continue

      try:
        # Check for py7zr library before attempting to use it.
        import py7zr
        with py7zr.SevenZipFile(compress_file_path, 'w') as archive:
          archive.write(log_file_path, arcname=os.path.basename(log_file_path))

        self.log.info(f"Compressed log file to: {compress_file_path}")
        compressed_count += 1
      except ImportError:
        self.log.error(f"Required library 'py7zr' is not installed. Halting compression. Please run 'pip install py7zr'.")
        # Stop further compression attempts if the library is missing.
        return
      except Exception as e:
        self.log.error(f"Failed to compress {log_file_path}: {e}")
    if compressed_count == 0:
      self.log.info("No new log files to compress.")

  def _cleanup_old_logs(self, all_log_files):
    """Deletes .log files that exceed the 'bak_count' threshold."""
    self.log.info("Step 2: Checking for old .log files to clean up...")
    if len(all_log_files) > self.bak_count:
      files_to_delete = all_log_files[:-self.bak_count]
      self.log.info(f"Found {len(files_to_delete)} old .log file(s) to remove.")
      for filename in files_to_delete:
        try:
          file_path = os.path.join(self.log_file_path, filename)
          os.remove(file_path)
          self.log.info(f"Removed old log file: {file_path}")
        except Exception as e:
          self.log.error(f"Failed to remove log file {filename}: {e}")
    else:
      self.log.info(f"Log file count ({len(all_log_files)}) is within the backup limit ({self.bak_count}). No cleanup needed.")

  def _cleanup_old_archives(self):
    """Deletes compressed archives that exceed the 'bak_count' threshold."""
    self.log.info("Step 3: Checking for old archives to clean up...")
    all_archive_files = self._get_sorted_files(self.archive_file_pattern)
    if len(all_archive_files) > self.bak_count:
      archives_to_delete = all_archive_files[:-self.bak_count]
      self.log.info(f"Found {len(archives_to_delete)} old archive(s) to remove.")
      for filename in archives_to_delete:
        try:
          file_path = os.path.join(self.log_file_path, filename)
          os.remove(file_path)
          self.log.info(f"Removed old archive file: {file_path}")
        except Exception as e:
          self.log.error(f"Failed to remove archive file {filename}: {e}")
    else:
      self.log.info(f"Archive count ({len(all_archive_files)}) is within the backup limit ({self.bak_count}). No cleanup needed.")

  def start(self):
    """
    Adds the archival job to the scheduler and starts it in a background thread.
    """
    cron = self.log_compress_schedule_cron
    try:
      # Check for apscheduler before trying to use it.
      from apscheduler.schedulers.background import BackgroundScheduler
      from apscheduler.triggers.cron import CronTrigger
      trigger = CronTrigger.from_crontab(cron)
      self.scheduler.add_job(self._run_archival_tasks, trigger)
      thread = threading.Thread(target=self.scheduler.start, daemon=True)
      thread.start()
      self.log.info(f"Log archiver scheduled with cron expression: '{cron}'.")
    except ImportError:
      self.log.error("Required library 'apscheduler' is not installed. Log archiver will not start. Please run 'pip install apscheduler'.")
    except Exception as e:
      self.log.error(f"Failed to schedule log archiver with cron expression '{cron}': {e}")
      raise

  def stop(self):
    """
    Stops the scheduler gracefully.
    """
    self.log.info("Stopping log archiver scheduler.")
    self.scheduler.shutdown()
