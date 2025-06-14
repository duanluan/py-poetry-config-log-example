# py-poetry-config-log-example

[Poetry](https://python-poetry.org/) 管理依赖，使用 [PyYAML](https://pyyaml.org/) 从 yml 读取配置，自定义 [logging](https://docs.python.org/3/library/logging.html) 生成日志，使用 [APScheduler](https://apscheduler.readthedocs.io/) 和 [py7zr](https://py7zr.readthedocs.io/) 定时压缩归档日志。

Use [Poetry](https://python-poetry.org/) to manage dependencies, read configuration from a YAML file using [PyYAML](https://pyyaml.org/), customize [logging](https://docs.python.org/3/library/logging.html) to generate logs, and use [APScheduler](https://apscheduler.readthedocs.io/) and [py7zr](https://py7zr.readthedocs.io/) to periodically compress and archive logs.

# 打包 Packaging EXE

## 首次构建 Initial Build

* `-F`单文件 Single-file executable，`-D`单目录 Single-directory executable
* `-n`exe 文件名 Specifies the name of the exe file
* `--add-data`添加资源文件 Adds resource files

```bash
pyinstaller -D src/main/setup.py -n main --add-data "res;res"
```

## 通过 .spec 文件构建 Build Using a .spec File

* `--noconfirm`无需确认是否覆盖上次构建的文件 No need to confirm whether to overwrite the last built file

```bash
pyinstaller main.spec --noconfirm
```

# 命令 Command

```shell
# 安装依赖 Install dependencies
poetry install

# 启动 Start the application
poetry run main
```
