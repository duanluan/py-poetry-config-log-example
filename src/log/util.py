import os
import re
import threading

from apscheduler.schedulers.background import BackgroundScheduler


def compressArchiveLog(log, logFilePath, logCompressLevel, logCompressSuffix='.7z'):
  """
  Compress archived log files.
  :param logFilePath: Path to the log file directory
  :param logCompressLevel: Compression level
  :param logCompressSuffix: File extension for compressed files
  :return:
  """

  def runCompressArchiveLog():
    logFileSuffix = '.log'

    # Get all .log files in the log directory
    logFiles = [logFilePath + "/" + file for file in os.listdir(logFilePath) if file.endswith(logFileSuffix)]
    for logFile in logFiles:
      # Skip files that do not contain a date pattern like _2024-01-01.log in their name
      if not re.search(r'_\d{4}-\d{2}-\d{2}' + logFileSuffix, logFile):
        log.info(f"Skipping non-archived log file: {logFile}")
        continue
      # Skip files that already have a corresponding .7z compressed file
      compressFile = logFile.replace(logFileSuffix, logCompressSuffix)
      if os.path.exists(compressFile):
        log.info(f"Skipping already compressed file: {logFile}")
        continue

      if logCompressSuffix == '.7z':
        import py7zr
        # Compress archived logs. The `with` statement ensures the file is released after compression.
        with py7zr.SevenZipFile(
            # Path to the compressed file
            compressFile,
            # Write mode: 'w' means write a new file, overwriting if it exists
            'w',
            filters=[{
              # Compression algorithm
              "id": py7zr.FILTER_LZMA2,
              # Compression level: 0~9, where 0 means no compression
              "preset": logCompressLevel
            }]
        ) as archive:
          archive.write(logFile, arcname=os.path.basename(logFile))
      elif logCompressSuffix == '.zip':
        import zipfile
        with zipfile.ZipFile(compressFile, 'w', zipfile.ZIP_DEFLATED) as archive:
          archive.write(logFile, arcname=os.path.basename(logFile))
      else:
        log.error(f"Unsupported compression file extension: {logCompressSuffix}")
        return
      log.info(f"Compressed log file to: {compressFile}")

  # Schedule the compression task to run daily at 1:00 AM
  scheduler = BackgroundScheduler()
  scheduler.add_job(runCompressArchiveLog, 'cron', hour=1)
  threading.Thread(target=scheduler.start).start()
