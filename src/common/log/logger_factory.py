import logging
import re
import sys
from logging import handlers
import os
import zipfile
from threading import RLock

# Attempt to import py7zr. Compression functionality will be disabled if the import fails.
# 尝试导入 py7zr。如果导入失败，压缩功能将被禁用。
try:
  import py7zr
except ImportError:
  py7zr = None

# Try to import APScheduler for periodic archival jobs.
# 尝试导入 APScheduler 以支持周期性归档任务。
try:
  from apscheduler.schedulers.background import BackgroundScheduler
  from apscheduler.triggers.cron import CronTrigger
except ImportError:
  BackgroundScheduler = None
  CronTrigger = None

# A mapping of log level names to their logging constants.
# 日志级别名称到其日志记录常量的映射。
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

SUPPORTED_ARCHIVE_SUFFIXES = {'.7z', '.zip'}


class ArchivingTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
  """
  A custom TimedRotatingFileHandler with archival and cleanup capabilities.
  一个自定义的 TimedRotatingFileHandler，支持归档与清理能力。

  - Compresses rotated .log files that haven't been archived yet. 压缩尚未归档的已轮替 .log 文件。
  - Retains a specified number of the most recent .log files based on backupCount. 根据 backupCount 保留指定数量的最新 .log 文件。
  - Retains a specified number of the most recent compressed files based on compress_backup_count. 根据 compress_backup_count 保留指定数量的最新压缩文件。
  """

  def __init__(
    self,
    filename,
    when='h',
    interval=1,
    backupCount=0,
    encoding=None,
    delay=False,
    utc=False,
    atTime=None,
    compress_suffix='.7z',
    compress_level=9,
    compress_backup_count=0,
    compress_schedule_cron=None,
  ):
    """
    Initializes the handler.
    初始化处理器。
    :param compress_suffix: The suffix for compressed files. 压缩文件的后缀名。
    :param compress_level: Compression level (0~9). 压缩级别（0~9）。
    :param compress_backup_count: The number of compressed files to keep (0 or negative means keep all). 要保留的压缩文件数量（0 或负数表示全部保留）。
    :param compress_schedule_cron: Cron expression for periodic archival. 定期归档任务的 Cron 表达式。
    """
    super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)

    # Store the original backupCount for our custom log cleanup logic.
    # 存储原始的 backupCount 以用于我们的自定义日志清理逻辑。
    self.real_backup_count = backupCount
    # Accept both "zip" and ".zip" formats and normalize.
    # 同时接受 "zip" 与 ".zip" 写法并标准化。
    suffix = (compress_suffix or '.7z')
    suffix = suffix.strip().lower() if isinstance(suffix, str) else str(suffix).strip().lower()
    if suffix and not suffix.startswith('.'):
      suffix = f'.{suffix}'
    self.compress_suffix = suffix or '.7z'

    # Clamp/validate compression level via int conversion.
    # 通过 int 转换规范压缩级别。
    self.compress_level = int(compress_level)

    # The number of compressed backups to retain.
    # 要保留的压缩备份数量。
    self.compress_backup_count = compress_backup_count
    self.compress_schedule_cron = (
      compress_schedule_cron.strip() if isinstance(compress_schedule_cron, str) else compress_schedule_cron
    )

    # Internal lock to avoid concurrent archival work from rollover and scheduler.
    # 内部锁，避免轮转与调度任务并发执行归档。
    self._archival_lock = RLock()
    self._scheduler = None
    self._py7zr_warning_emitted = False
    self._retention_warning_emitted = False

    if self.compress_suffix not in SUPPORTED_ARCHIVE_SUFFIXES:
      supported = ', '.join(sorted(SUPPORTED_ARCHIVE_SUFFIXES))
      raise ValueError(f"Unsupported compress_suffix '{compress_suffix}'. Supported values: {supported}")

    if not 0 <= self.compress_level <= 9:
      raise ValueError(f"compress_level must be within [0, 9], got {self.compress_level}")

    # Infer the base name pattern from the log filename to match related files.
    # 从日志文件名推断基础名称模式，以匹配相关文件。
    base_filename = os.path.basename(filename)
    self.base_name_pattern = os.path.splitext(base_filename)[0]

    # Matches filenames like 'app1_251003.log' or 'app1_251003_143000.log'.
    # 匹配像 'app1_251003.log' 或 'app1_251003_143000.log' 这样的文件名。
    self.log_file_pattern = re.compile(rf"^{re.escape(self.base_name_pattern)}_\d{{6}}(_\d{{6}})?\.log$")
    # Matches corresponding archive filenames.
    # 匹配相应的归档文件名。
    self.archive_file_pattern = re.compile(rf"^{re.escape(self.base_name_pattern)}_\d{{6}}(_\d{{6}})?{re.escape(self.compress_suffix)}$")

    # Start scheduled archival if cron is configured.
    # 如果配置了 cron，则启动定时归档任务。
    if self.compress_schedule_cron:
      self._start_scheduler(self.compress_schedule_cron)

  def close(self):
    # Ensure scheduler is shutdown with handler lifecycle.
    # 确保处理器关闭时同步停止调度器。
    if self._scheduler is not None:
      try:
        self._scheduler.shutdown(wait=False)
      except Exception:
        pass
      self._scheduler = None

    # Run a best-effort archival pass on shutdown so recently rotated logs are not left uncompressed.
    # 在关闭时执行一次尽力归档，避免最近轮替日志未被压缩。
    try:
      self._run_archival_tasks()
    except Exception as e:
      self._warn(f"Final archival pass failed during handler close: {e}")

    super().close()

  def doRollover(self):
    """
    Performs log rotation.
    执行日志轮替。
    """
    # First, call the parent class's method to perform the standard log file rollover.
    # 首先，调用父类的方法来执行标准的日志文件轮替。
    super().doRollover()
    # If no cron schedule is configured, run archival right after rollover.
    # 如果未配置 cron 调度，则在轮替后立即执行归档。
    if not self.compress_schedule_cron:
      self._run_archival_tasks()

  def _warn(self, message):
    # Avoid recursive logging when handler internals fail.
    # 避免处理器内部失败时触发递归日志。
    sys.stderr.write(f"[log-archiver] {message}\n")

  def _start_scheduler(self, cron_expression):
    if BackgroundScheduler is None or CronTrigger is None:
      raise RuntimeError("APScheduler is required when 'compress-schedule-cron' is configured.")

    try:
      trigger = CronTrigger.from_crontab(cron_expression)
    except ValueError as e:
      raise ValueError(
        f"Invalid compress_schedule_cron '{cron_expression}'. Expected crontab format like '0 1 * * *'."
      ) from e

    # Use daemon scheduler to avoid blocking application exit.
    # 使用守护线程调度器，避免阻塞应用退出。
    self._scheduler = BackgroundScheduler(daemon=True)
    self._scheduler.add_job(
      self._run_archival_tasks,
      trigger=trigger,
      id=f"log-archival-{id(self)}",
      replace_existing=True,
      max_instances=1,
      coalesce=True,
    )
    self._scheduler.start()

  def _get_sorted_files(self, pattern):
    """
    Finds and sorts files in the log directory based on a given regex pattern.
    根据给定的正则表达式模式，在日志目录中查找并排序文件。
    """
    dir_path = os.path.dirname(self.baseFilename)
    try:
      # List all files in the directory, filter by the pattern, and sort them.
      # 列出目录中的所有文件，按模式过滤，然后对它们进行排序。
      files = [f for f in os.listdir(dir_path) if pattern.match(f)]
      files.sort()
      return files
    except OSError:
      return []

  def _archive_file_path(self, log_file_path):
    return os.path.splitext(log_file_path)[0] + self.compress_suffix

  def _has_archive(self, log_file_path):
    return os.path.exists(self._archive_file_path(log_file_path))

  def _compress_with_7z(self, log_file_path, archive_file_path):
    if py7zr is None:
      raise RuntimeError("py7zr is required for '.7z' compression.")

    filters = [{"id": py7zr.FILTER_LZMA2, "preset": self.compress_level}]
    with py7zr.SevenZipFile(archive_file_path, mode='w', filters=filters) as archive:
      archive.write(log_file_path, arcname=os.path.basename(log_file_path))

  def _compress_with_zip(self, log_file_path, archive_file_path):
    compression = zipfile.ZIP_STORED if self.compress_level == 0 else zipfile.ZIP_DEFLATED
    zip_kwargs = {"compression": compression}
    if compression == zipfile.ZIP_DEFLATED:
      zip_kwargs["compresslevel"] = self.compress_level

    with zipfile.ZipFile(archive_file_path, mode='w', **zip_kwargs) as archive:
      archive.write(log_file_path, arcname=os.path.basename(log_file_path))

  def _compress_new_logs(self, all_log_files):
    """
    Compresses any .log files that do not have a corresponding archive file.
    压缩任何没有对应归档文件的 .log 文件。
    """
    # Skip compression if the py7zr library is not installed.
    # 如果未安装 py7zr 库，则跳过压缩。
    if self.compress_suffix == '.7z' and py7zr is None:
      if not self._py7zr_warning_emitted:
        self._warn("py7zr is not installed; skipping .7z compression.")
        self._py7zr_warning_emitted = True
      return

    dir_path = os.path.dirname(self.baseFilename)
    for log_filename in all_log_files:
      log_file_path = os.path.join(dir_path, log_filename)
      # Construct the corresponding archive filename.
      # 构建相应的归档文件名。
      compress_file_path = self._archive_file_path(log_file_path)

      if os.path.exists(compress_file_path):
        # Skip if the archive already exists.
        # 如果归档文件已存在，则跳过。
        continue

      try:
        # Create the archive using py7zr.
        # 使用 py7zr 创建归档文件。
        if self.compress_suffix == '.zip':
          self._compress_with_zip(log_file_path, compress_file_path)
        else:
          self._compress_with_7z(log_file_path, compress_file_path)
      except Exception as e:
        # Silently skip on error to avoid interrupting the logging process.
        # 为避免中断日志记录过程，在出错时静默跳过。
        # Remove broken archive if compression failed.
        # 如果压缩失败，删除损坏的归档文件，保留原日志供后续重试。
        try:
          if os.path.exists(compress_file_path):
            os.remove(compress_file_path)
        except OSError:
          pass
        self._warn(f"Failed to compress '{log_file_path}' to '{compress_file_path}': {e}")

  def _cleanup_old_logs(self, all_log_files):
    """
    Deletes the oldest .log files that exceed the backupCount limit.
    删除超出 backupCount 限制的最旧的 .log 文件。
    """
    if self.real_backup_count > 0 and len(all_log_files) > self.real_backup_count:
      dir_path = os.path.dirname(self.baseFilename)
      # Select the oldest files to delete from the sorted list.
      # 从排序列表中选择要删除的最旧的文件。
      files_to_delete = all_log_files[:-self.real_backup_count]
      for filename in files_to_delete:
        log_file_path = os.path.join(dir_path, filename)

        # Data-safety rule: only remove logs that are already archived.
        # 数据安全规则：仅删除已归档的日志，避免压缩失败导致日志丢失。
        if not self._has_archive(log_file_path):
          self._warn(f"Skip deleting unarchived log file '{log_file_path}'.")
          continue

        try:
          os.remove(log_file_path)
        except OSError as e:
          self._warn(f"Failed to delete old log file '{log_file_path}': {e}")

  def _cleanup_old_archives(self):
    """
    Deletes the oldest compressed files that exceed the compress_backup_count limit.
    删除超出 compress_backup_count 限制的最旧的压缩文件。
    """
    # If compress_backup_count is non-positive, do nothing (keep all archives).
    # 如果 compress_backup_count 是非正数，则不执行任何操作（保留所有归档）。
    if self.compress_backup_count <= 0:
      return

    # Avoid repeated recompression when archive retention is lower than log retention by keeping at least backupCount archives.
    # 当归档保留数低于日志保留数时，至少保留 backupCount 份归档以避免重复压缩。
    effective_archive_keep = max(self.compress_backup_count, self.real_backup_count)
    if (
      effective_archive_keep != self.compress_backup_count
      and not self._retention_warning_emitted
    ):
      self._warn(
        f"compress_backup_count={self.compress_backup_count} is smaller than "
        f"backupCount={self.real_backup_count}; effective archive retention is "
        f"raised to {effective_archive_keep} to avoid repeated recompression."
      )
      self._retention_warning_emitted = True

    all_archive_files = self._get_sorted_files(self.archive_file_pattern)

    # Check if the number of archives exceeds the limit.
    # 检查归档文件的数量是否超过限制。
    if len(all_archive_files) > effective_archive_keep:
      dir_path = os.path.dirname(self.baseFilename)
      archives_to_delete = all_archive_files[:-effective_archive_keep]
      for filename in archives_to_delete:
        try:
          os.remove(os.path.join(dir_path, filename))
        except OSError as e:
          self._warn(f"Failed to delete old archive '{filename}': {e}")

  def _run_archival_tasks(self):
    """
    Executes all archival tasks in sequence: compression, log cleanup, and archive cleanup.
    按顺序执行所有归档任务：压缩、日志清理和归档清理。
    """
    with self._archival_lock:
      # Get all rotated log files.
      # 获取所有已轮替的日志文件。
      all_log_files = self._get_sorted_files(self.log_file_pattern)
      if not all_log_files:
        return

      self._compress_new_logs(all_log_files)
      self._cleanup_old_logs(all_log_files)
      # Clean up old compressed archives.
      # 清理旧的压缩归档文件。
      self._cleanup_old_archives()


def _namer(name):
  """
  Custom namer for log rotation to meet the "app1_YYMMDD_HHMMSS.log" format.
  用于日志轮替的自定义命名器，以满足 "app1_YYMMDD_HHMMSS.log" 的格式。
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


def create_logger(
  logger_name,
  log_file_path='app.log',
  level='info',
  when='midnight',
  bak_count=30,
  fmt='%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s',
  compress_suffix='.7z',
  compress_bak_count=90,
  compress_level=9,
  compress_schedule_cron=None,
):
  """
  Factory function to create and configure a logger instance.
  用于创建和配置日志记录器实例的工厂函数。
  """
  logger = logging.getLogger(logger_name)

  level = level.lower() if isinstance(level, str) else 'info'
  valid_level = _levelRelations.get(level, logging.INFO)

  log_formatter = logging.Formatter(fmt)

  new_stream_handler = None
  new_file_handler = None
  try:
    new_stream_handler = logging.StreamHandler(sys.stdout)
    new_stream_handler.setFormatter(log_formatter)

    # Use our full-featured ArchivingTimedRotatingFileHandler.
    # 使用我们功能齐全的 ArchivingTimedRotatingFileHandler。
    new_file_handler = ArchivingTimedRotatingFileHandler(
      filename=log_file_path,
      when=when,
      backupCount=bak_count,
      encoding='utf-8',
      compress_suffix=compress_suffix,
      compress_level=compress_level,
      # Pass the parameter for compressed backup count.
      # 传入用于压缩备份计数的参数。
      compress_backup_count=compress_bak_count,
      compress_schedule_cron=compress_schedule_cron,
    )
    new_file_handler.setFormatter(log_formatter)
    new_file_handler.namer = _namer
  except Exception:
    if new_stream_handler is not None:
      try:
        new_stream_handler.close()
      except Exception:
        pass
    if new_file_handler is not None:
      try:
        new_file_handler.close()
      except Exception:
        pass
    raise

  # Atomic reconfiguration: build new handlers first, then swap.
  # 原子重配：先创建新 handlers，再替换旧 handlers。
  old_handlers = list(logger.handlers)
  old_level = logger.level
  old_propagate = logger.propagate
  try:
    logger.setLevel(valid_level)
    logger.propagate = False

    for handler in old_handlers:
      logger.removeHandler(handler)

    logger.addHandler(new_stream_handler)
    logger.addHandler(new_file_handler)
  except Exception:
    # Roll back to previous logger state if swap fails.
    # 若替换失败，回滚到旧 logger 状态。
    try:
      if new_stream_handler in logger.handlers:
        logger.removeHandler(new_stream_handler)
      new_stream_handler.close()
    except Exception:
      pass

    try:
      if new_file_handler in logger.handlers:
        logger.removeHandler(new_file_handler)
      new_file_handler.close()
    except Exception:
      pass

    logger.setLevel(old_level)
    logger.propagate = old_propagate
    for handler in old_handlers:
      if handler not in logger.handlers:
        logger.addHandler(handler)
    raise

  # New handlers are active, now close previous handlers.
  # 新 handlers 生效后，再关闭旧 handlers。
  for handler in old_handlers:
    try:
      handler.close()
    except Exception:
      pass

  return logger
