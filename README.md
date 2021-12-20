# payload dumper

Dumps the `payload.bin` image found in Android update images.

## Installation

### Requirements

- Python3
- pip

### Install using pip

```sh
pip install --user payload_dumper
```

## Usage

### Dumping the entirety of `payload.bin`

```
payload_dumper payload.bin
```

### Dumping specific partitions

Use a comma-separated list of partitions to dump:
```
payload_dumper --partitions boot,dtbo,vendor
```

### Patching older image with OTA

Assuming the old partitions are in a directory named `old/`:
```
payload_dumper --diff payload.bin
```
