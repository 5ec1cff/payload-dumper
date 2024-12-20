# payload dumper of online

[中文](docs/README.zh-CN.md)

This is a modified version of payload dumper that supports the following features in addition to the original features:

1. Extract partitions directly from a zip archive containing payload.bin without unzipping it.   
2. Extract partitions directly from a URL (such as an OTA update URL) containing payload.bin from the network without downloading the entire file.  

With this script, you only need a small amount of time and storage space to extract the partitions you want from the OTA update package or address, especially the smaller partitions such as boot, init_boot, vbmeta, etc.

Future Outlook: Maybe it can support extracting some files in system partitions?

## usage

```bash
pip install git+https://github.com/5ec1cff/payload-dumper
payload_dumper --partitions <partitions you need> <file path or url>
```
---

# payload dumper

Dumps the `payload.bin` image found in Android update images. Has significant performance gains over other tools due to using multiprocessing.

## Installation

### Requirements

- Python3 >= 3.12
- pip

## Usage

### Dumping the entirety of `payload.bin`

```bash
payload_dumper payload.bin
```

### Dumping specific partitions

Use a comma-separated list of partitions to dump:
```bash
payload_dumper --partitions boot,dtbo,vendor payload.bin
```

### Patching older image with OTA

Assuming the old partitions are in a directory named `old/`:
```bash
payload_dumper --diff payload.bin
```

## Developing

```shell
git clone https://github.com/5ec1cff/payload-dumper
# run
cd src
python -m payload_dumper
# install
cd ..
pip install .
```

