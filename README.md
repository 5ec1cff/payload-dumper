# payload dumper of online

这是一个修改版的 payload dumper ，除了具有它原先支持的功能，还支持以下特性：

1. 从包含 payload.bin 的 zip 归档中直接提取分区，而无需解压。  
2. 从来自网络的包含 payload.bin （的 zip 归档）的 url （如 OTA 更新地址）直接提取分区，而无需下载整个文件。

借助该脚本，你只需要少量的时间和存储空间就能从 OTA 更新包或地址中提取你想要的分区，尤其是比较小的分区，如 boot, init_boot, vbmeta 等。

未来展望：也许可以让它支持提取系统分区中的部分文件？

---

This is a modified version of payload dumper that supports the following features in addition to the original features:

1. Extract partitions directly from a zip archive containing payload.bin without unzipping it.   
2. Extract partitions directly from a URL (such as an OTA update URL) containing payload.bin from the network without downloading the entire file.  

With this script, you only need a small amount of time and storage space to extract the partitions you want from the OTA update package or address, especially the smaller partitions such as boot, init_boot, vbmeta, etc.

Future Outlook: Maybe it can support extracting some files in system partitions?

## usage

```commandline
git clone https://github.com/5ec1cff/payload-dumper
cd payload-dumper
pip install -r requirement.txt
cd payload_dumper
python dumper.py --partitions <partitions you need> <file path or url>
```
---

# payload dumper

Dumps the `payload.bin` image found in Android update images. Has significant performance gains over other tools due to using multiprocessing.

## Installation

### Requirements

- Python3
- pip

## Example ASCIIcast

[![asciicast](https://asciinema.org/a/UbDZGZwCXux50sSzy1fc1bhaO.svg)](https://asciinema.org/a/UbDZGZwCXux50sSzy1fc1bhaO)

## Usage

### Dumping the entirety of `payload.bin`

```
payload_dumper payload.bin
```

### Dumping specific partitions

Use a comma-separated list of partitions to dump:
```
payload_dumper --partitions boot,dtbo,vendor payload.bin
```

### Patching older image with OTA

Assuming the old partitions are in a directory named `old/`:
```
payload_dumper --diff payload.bin
```
