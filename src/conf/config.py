import argparse
import os
from pathlib import Path

import yaml


def loadConfigYml(configFileRelPath):
  """
  Load the configuration file.
  :param configFileRelPath: Relative path to the configuration file based on the current script
  :return: Configuration dictionary
  """
  # Parse command-line arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('--config', type=str, help='yml config file')
  args, _ = parser.parse_known_args()

  # If a configuration file is specified via command-line arguments
  if args.config:
    # Get the absolute path of the configuration file
    configFileAbsPath = os.path.abspath(args.config)
  else:
    # Get the absolute path of the default configuration file relative to the current script
    projectDir = Path(__file__).parents[2]
    configFileAbsPath = os.path.join(projectDir, configFileRelPath)

  try:
    # Read the configuration file
    with open(configFileAbsPath, 'r', encoding='utf-8') as filePath:
      return yaml.load(filePath, Loader=yaml.FullLoader)
  except Exception:
    raise Exception(f"Failed to read the configuration file: {configFileAbsPath}")
