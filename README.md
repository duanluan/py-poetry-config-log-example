# py-poetry-config-log-example

poetry 管理依赖，从 yml 读取配置，自定义 logging 生成日志，定时任务压缩归档日志。

Using Poetry to manage dependencies, loading configurations from a YAML file, customizing logging for generating logs, and using scheduled tasks to compress and archive logs.

# 打包 Packaging EXE

## 首次构建 Initial Build

* `-F`单文件 Single-file executable，`-D`单目录 Single-directory executable
* `-n`exe 文件名 Specifies the name of the exe file
* `--add-data`添加资源文件 Adds resource files

```bash
pyinstaller -D src/main/setup.py -n main --add-data "res;res"
```

## 通过 .spec 文件构建 Build Using a .spec File
```bash
pyinstaller main.spec
```
