# payload dumper of online

这是一个修改版的 payload dumper ，除了具有它原先支持的功能，还支持以下特性：

1. 从包含 payload.bin 的 zip 归档中直接提取分区，而无需解压。  
2. 从来自网络的包含 payload.bin （的 zip 归档）的 url （如 OTA 更新地址）直接提取分区，而无需下载整个文件。

借助该脚本，你只需要少量的时间和存储空间就能从 OTA 更新包或地址中提取你想要的分区，尤其是比较小的分区，如 boot, init_boot, vbmeta 等。

未来展望：也许可以让它支持提取系统分区中的部分文件？

## 用法

```bash
pip install git+https://github.com/5ec1cff/payload-dumper
payload_dumper --partitions <partitions you need> <file path or url>
```
---

# payload dumper

转储 Android 更新镜像中的 `payload.bin` 镜像。由于使用了多进程，性能比其他工具有明显提高。

## Installation

### Requirements

- Python3 >= 3.12
- pip

## Usage

### 转储整个 `payload.bin` 文件

```bash
payload_dumper payload.bin
```

### 转储特定分区

使用逗号分隔的要转储的分区列表：
```bash
payload_dumper --partitions boot,dtbo,vendor payload.bin
```


### 使用 OTA 修补旧镜像

假设旧分区位于名为 `old/` 的目录中：
```bash
payload_dumper --diff payload.bin
```
