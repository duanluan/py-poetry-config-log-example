# py-poetry-config-log-example

[English](./README.md) | [简体中文](./README_CN.md)

Use [Poetry](https://python-poetry.org/) to manage dependencies, load YAML configuration via [PyYAML](https://pyyaml.org/), generate rotating logs with [logging](https://docs.python.org/3/library/logging.html), and compress archived logs using [APScheduler](https://apscheduler.readthedocs.io/) and [py7zr](https://py7zr.readthedocs.io/).

## Quick Start (First Run)

```shell
# Globally set the virtual environment to be created in the project's .venv directory
poetry config virtualenvs.in-project true

# Temporarily set the virtual environment to be created in the project's .venv directory
# Linux
POETRY_VIRTUALENVS_IN_PROJECT=true
# Windows CMD
set POETRY_VIRTUALENVS_IN_PROJECT=true
# Windows PowerShell
$env:POETRY_VIRTUALENVS_IN_PROJECT="true"

# Install dependencies (by default in the virtualenvs directory under "poetry config cache-dir")
poetry install

# Run app script entry
poetry run app1


# Show the command to activate the virtual environment
poetry env info -p
# Activate the virtual environment (Windows)
.venv\Scripts\activate.bat
# Deactivate the virtual environment (Windows)
.venv\Scripts\deactivate.bat

# Remove the virtual environment
poetry env remove python
```

Notes:

- `poetry run` does not require manually activating `.venv`.
- If dependencies or lockfile change, run `poetry install` again.

## Daily Run

```shell
poetry run app1
```

Optional one-off module form:

```shell
poetry run python -m app1.app1
```

## Usage in PyCharm

Set once, then reuse:

1. Interpreter: select project `.venv` (Poetry-created environment).
2. Mark `src` as `Sources Root` in Project view.
3. Run Configuration:
   - Type: Python
   - Run: `Module name`
   - Module name: `app1.app1`
   - Working directory: project root
4. Save the run configuration (optionally as shared).

If you see `ModuleNotFoundError: No module named 'app1'` or `'common'`:

```shell
poetry install
```

## Packaging EXE

Initial build:

- `-F` single-file executable, `-D` single-directory executable
- `-n` executable name
- `--add-data` include resource files
- `-p` append search path to `sys.path`

```shell
pyinstaller -n app1 -D --add-data "src/app1/res;res" -p src src/app1/app1.py
```

Build with `.spec`:

- `--noconfirm` No need to confirm whether to overwrite the last built file

```shell
pyinstaller app1.spec --noconfirm
```

Run EXE:

```shell
app1.exe --config _internal\res\config.yml
```
