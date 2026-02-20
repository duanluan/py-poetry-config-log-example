# py-poetry-config-log-example

[English](./README.md) | [简体中文](./README_CN.md)

使用 [Poetry](https://python-poetry.org/) 管理依赖，使用 [PyYAML](https://pyyaml.org/) 读取 YAML 配置，基于 [logging](https://docs.python.org/3/library/logging.html) 输出并轮转日志，再结合 [APScheduler](https://apscheduler.readthedocs.io/) 和 [py7zr](https://py7zr.readthedocs.io/) 对归档日志进行压缩清理。

## 快速开始（首次运行）

```shell
# 全局设置虚拟环境在项目目录 .venv
poetry config virtualenvs.in-project true

# 临时设置虚拟环境在项目目录 .venv
# Linux
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install
# Windows CMD
set POETRY_VIRTUALENVS_IN_PROJECT=true
# Windows PowerShell
$env:POETRY_VIRTUALENVS_IN_PROJECT="true"

# 安装依赖（默认在“poetry config cache-dir”下的 virtualenvs 目录中）
poetry install

# 运行应用脚本入口
poetry run app1


# 查看激活虚拟环境脚本
poetry env activate
# 激活虚拟环境（Windows）
.venv\Scripts\activate.bat
# 退出虚拟环境（Windows）
.venv\Scripts\deactivate.bat

# 删除虚拟环境
poetry env remove python
```

说明：

- `poetry run` 无需手动激活 `.venv`。
- 若依赖或锁文件有变更，请重新执行 `poetry install`。

## 日常运行

```shell
poetry run app1
```

可选的一次性模块运行方式：

```shell
poetry run python -m app1.app1
```

## 在 PyCharm 中使用

一次设置后可长期复用：

1. Interpreter：选择项目 `.venv`（Poetry 创建的虚拟环境）。
2. 在 Project 视图中将 `src` 标记为 `Sources Root`。
3. 新建 Run Configuration：
   - Type：Python
   - Run：`Module name`
   - Module name：`app1.app1`
   - Working directory：项目根目录
4. 保存该配置（可选设为 shared）。

如果出现 `ModuleNotFoundError: No module named 'app1'` 或 `'common'`：

```shell
poetry install
```

## 打包 EXE

首次构建：

- `-F` 单文件，`-D` 单目录
- `-n` EXE 文件名
- `--add-data` 添加资源文件
- `-p` 添加模块搜索路径（`sys.path`）

```shell
pyinstaller -n app1 -D --add-data "src/app1/res;res" -p src src/app1/app1.py
```

通过 `.spec` 构建：

- `--noconfirm`无需确认是否覆盖上次构建的文件

```shell
pyinstaller app1.spec --noconfirm
```

运行 EXE：

```shell
app1.exe --config _internal\res\config.yml
```
