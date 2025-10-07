import logging
import re
import sys
from logging import handlers
import os

# Attempt to import py7zr. Compression functionality will be disabled if the import fails.
# 尝试导入 py7zr。如果导入失败，压缩功能将被禁用。
try:
    import py7zr
except ImportError:
    py7zr = None

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


class ArchivingTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    A custom TimedRotatingFileHandler that automatically performs compression and cleanup during log rotation.
    一个自定义的 TimedRotatingFileHandler，它会在日志轮替期间自动执行压缩和清理。

    - Compresses rotated .log files that haven't been archived yet. 压缩尚未归档的已轮替 .log 文件。
    - Retains a specified number of the most recent .log files based on backupCount. 根据 backupCount 保留指定数量的最新 .log 文件。
    - Retains a specified number of the most recent compressed files based on compress_backup_count. 根据 compress_backup_count 保留指定数量的最新压缩文件。
    """
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None, compress_suffix='.7z', compress_backup_count=0):
        """
        Initializes the handler.
        初始化处理器。
        :param compress_suffix: The suffix for compressed files. 压缩文件的后缀名。
        :param compress_backup_count: The number of compressed files to keep (0 or negative means keep all). 要保留的压缩文件数量（0 或负数表示全部保留）。
        """
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        # Store the original backupCount for our custom log cleanup logic.
        # 存储原始的 backupCount 以用于我们的自定义日志清理逻辑。
        self.real_backup_count = backupCount
        self.compress_suffix = compress_suffix
        # The number of compressed backups to retain.
        # 要保留的压缩备份数量。
        self.compress_backup_count = compress_backup_count

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

    def doRollover(self):
        """
        Performs log rotation, followed by archiving and cleanup tasks.
        执行日志轮替，然后执行归档和清理任务。
        """
        # First, call the parent class's method to perform the standard log file rollover.
        # 首先，调用父类的方法来执行标准的日志文件轮替。
        super().doRollover()
        # Then, immediately execute our custom archival tasks.
        # 然后，立即执行我们的自定义归档任务。
        self._run_archival_tasks()

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

    def _run_archival_tasks(self):
        """
        Executes all archival tasks in sequence: compression, log cleanup, and archive cleanup.
        按顺序执行所有归档任务：压缩、日志清理和归档清理。
        """
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

    def _compress_new_logs(self, all_log_files):
        """
        Compresses any .log files that do not have a corresponding archive file.
        压缩任何没有对应归档文件的 .log 文件。
        """
        if not py7zr:
            # Skip compression if the py7zr library is not installed.
            # 如果未安装 py7zr 库，则跳过压缩。
            return

        dir_path = os.path.dirname(self.baseFilename)
        for log_filename in all_log_files:
            log_file_path = os.path.join(dir_path, log_filename)
            # Construct the corresponding archive filename.
            # 构建相应的归档文件名。
            compress_file_path = os.path.splitext(log_file_path)[0] + self.compress_suffix

            if os.path.exists(compress_file_path):
                # Skip if the archive already exists.
                # 如果归档文件已存在，则跳过。
                continue

            try:
                # Create the archive using py7zr.
                # 使用 py7zr 创建归档文件。
                with py7zr.SevenZipFile(compress_file_path, 'w') as archive:
                    archive.write(log_file_path, arcname=os.path.basename(log_file_path))
            except Exception:
                # Silently skip on error to avoid interrupting the logging process.
                # 为避免中断日志记录过程，在出错时静默跳过。
                pass

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
                try:
                    os.remove(os.path.join(dir_path, filename))
                except OSError:
                    pass

    def _cleanup_old_archives(self):
        """
        Deletes the oldest compressed files that exceed the compress_backup_count limit.
        删除超出 compress_backup_count 限制的最旧的压缩文件。
        """
        # If compress_backup_count is non-positive, do nothing (keep all archives).
        # 如果 compress_backup_count 是非正数，则不执行任何操作（保留所有归档）。
        if self.compress_backup_count <= 0:
            return

        all_archive_files = self._get_sorted_files(self.archive_file_pattern)

        # Check if the number of archives exceeds the limit.
        # 检查归档文件的数量是否超过限制。
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


def create_logger(logger_name, log_file_path='app.log', level='info', when='midnight', bak_count=30, fmt='%(asctime)s %(levelname)s %(module)s.py, line %(lineno)d - %(message)s', compress_suffix='.7z', compress_bak_count=90):
  """
  Factory function to create and configure a logger instance.
  用于创建和配置日志记录器实例的工厂函数。
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
  # 使用我们功能齐全的 ArchivingTimedRotatingFileHandler。
  file_handler = ArchivingTimedRotatingFileHandler(
    filename=log_file_path,
    when=when,
    backupCount=bak_count,
    encoding='utf-8',
    compress_suffix=compress_suffix,
    # Pass the parameter for compressed backup count.
    # 传入用于压缩备份计数的参数。
    compress_backup_count=compress_bak_count
  )
  file_handler.setFormatter(log_formatter)
  file_handler.namer = _namer
  logger.addHandler(file_handler)

  return logger
