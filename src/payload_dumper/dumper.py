#!/usr/bin/env python
import bz2
import hashlib
import io
import json
import lzma
import os
import struct
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count

import bsdiff4
from enlighten import get_manager

from . import http_file
from . import update_metadata_pb2 as um

flatten = lambda l: [item for sublist in l for item in sublist]


def u32(x):
    return struct.unpack(">I", x)[0]


def u64(x):
    return struct.unpack(">Q", x)[0]


def verify_contiguous(exts):
    blocks = 0
    for ext in exts:
        if ext.start_block != blocks:
            return False

        blocks += ext.num_blocks

    return True


class Dumper:
    def __init__(
        self, payloadfile, out, diff=None, old=None, images="", workers=cpu_count(), list_partitions=False, extract_metadata=False
    ):
        self.payloadfile = payloadfile
        self.manager = get_manager()
        self.download_progress = None
        if isinstance(payloadfile, http_file.HttpFile):
            payloadfile.progress_reporter = self.update_download_progress
        self.out = out
        self.diff = diff
        self.old = old
        self.images = images
        self.workers = workers
        self.list_partitions = list_partitions
        self.extract_metadata = extract_metadata

        if self.extract_metadata:
            self.extract_and_display_metadata()
        else:
            try:
                self.parse_metadata()
            except AssertionError:
                # try zip
                with zipfile.ZipFile(self.payloadfile, "r") as zip_file:
                    self.payloadfile = zip_file.open("payload.bin", "r")
                self.parse_metadata()
                pass

            if self.list_partitions:
                self.list_partitions_info()

    def update_download_progress(self, prog, total):
        if self.download_progress is None and prog != total:
            self.download_progress = self.manager.counter(
                total=total, desc="download", unit="b", leave=False
            )
        if self.download_progress is not None:
            self.download_progress.update(prog - self.download_progress.count)
            if prog == total:
                self.download_progress.close()
                self.download_progress = None

    def run(self):
        if self.list_partitions or self.extract_metadata:
            return

        if self.images == "":
            partitions = self.dam.partitions
        else:
            partitions = []
            for image in self.images.split(","):
                image = image.strip()
                found = False
                for dam_part in self.dam.partitions:
                    if dam_part.partition_name == image:
                        partitions.append(dam_part)
                        found = True
                        break
                if not found:
                    print("Partition %s not found in image" % image)

        if len(partitions) == 0:
            print("Not operating on any partitions")
            return 0

        partitions_with_ops = []
        for partition in partitions:
            operations = []
            for operation in partition.operations:
                self.payloadfile.seek(self.data_offset + operation.data_offset)
                operations.append(
                    {
                        "operation": operation,
                        "data": self.payloadfile.read(operation.data_length),
                    }
                )
            partitions_with_ops.append(
                {
                    "partition": partition,
                    "operations": operations,
                }
            )

        self.payloadfile.close()

        self.multiprocess_partitions(partitions_with_ops)
        self.manager.stop()

    def multiprocess_partitions(self, partitions):
        progress_bars = {}

        def update_progress(partition_name, count):
            progress_bars[partition_name].update(count)

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for part in partitions:
                partition_name = part["partition"].partition_name
                progress_bars[partition_name] = self.manager.counter(
                    total=len(part["operations"]),
                    desc=f"{partition_name}",
                    unit="ops",
                    leave=True,
                )

            futures = {
                executor.submit(self.dump_part, part, update_progress): part
                for part in partitions
            }

            for future in as_completed(futures):
                part = futures[future]
                partition_name = part["partition"].partition_name
                try:
                    future.result()
                    progress_bars[partition_name].close()
                except Exception as exc:
                    print(f"{partition_name} - processing generated an exception: {exc}")
                    progress_bars[partition_name].close()

    def parse_metadata(self):
        head_len = 4 + 8 + 8 + 4
        buffer = self.payloadfile.read(head_len)
        assert len(buffer) == head_len
        magic = buffer[:4]
        assert magic == b"CrAU"

        file_format_version = u64(buffer[4:12])
        assert file_format_version == 2

        manifest_size = u64(buffer[12:20])

        metadata_signature_size = 0

        if file_format_version > 1:
            metadata_signature_size = u32(buffer[20:24])

        manifest = self.payloadfile.read(manifest_size)
        self.metadata_signature = self.payloadfile.read(metadata_signature_size)
        self.data_offset = self.payloadfile.tell()
        self.dam = um.DeltaArchiveManifest()
        self.dam.ParseFromString(manifest)
        self.block_size = self.dam.block_size

    def data_for_op(self, operation, out_file, old_file):
        data = operation["data"]
        op = operation["operation"]

        # assert hashlib.sha256(data).digest() == op.data_sha256_hash, 'operation data hash mismatch'

        if op.type == op.REPLACE_XZ:
            dec = lzma.LZMADecompressor()
            data = dec.decompress(data)
            out_file.seek(op.dst_extents[0].start_block * self.block_size)
            out_file.write(data)
        elif op.type == op.REPLACE_BZ:
            dec = bz2.BZ2Decompressor()
            data = dec.decompress(data)
            out_file.seek(op.dst_extents[0].start_block * self.block_size)
            out_file.write(data)
        elif op.type == op.REPLACE:
            out_file.seek(op.dst_extents[0].start_block * self.block_size)
            out_file.write(data)
        elif op.type == op.SOURCE_COPY:
            if not self.diff:
                print("SOURCE_COPY supported only for differential OTA")
                sys.exit(-2)
            out_file.seek(op.dst_extents[0].start_block * self.block_size)
            for ext in op.src_extents:
                old_file.seek(ext.start_block * self.block_size)
                data = old_file.read(ext.num_blocks * self.block_size)
                out_file.write(data)
        elif op.type == op.SOURCE_BSDIFF:
            if not self.diff:
                print("SOURCE_BSDIFF supported only for differential OTA")
                sys.exit(-3)
            out_file.seek(op.dst_extents[0].start_block * self.block_size)
            tmp_buff = io.BytesIO()
            for ext in op.src_extents:
                old_file.seek(ext.start_block * self.block_size)
                old_data = old_file.read(ext.num_blocks * self.block_size)
                tmp_buff.write(old_data)
            tmp_buff.seek(0)
            old_data = tmp_buff.read()
            tmp_buff.seek(0)
            tmp_buff.write(bsdiff4.patch(old_data, data))
            n = 0
            tmp_buff.seek(0)
            for ext in op.dst_extents:
                tmp_buff.seek(n * self.block_size)
                n += ext.num_blocks
                data = tmp_buff.read(ext.num_blocks * self.block_size)
                out_file.seek(ext.start_block * self.block_size)
                out_file.write(data)
        elif op.type == op.ZERO:
            for ext in op.dst_extents:
                out_file.seek(ext.start_block * self.block_size)
                out_file.write(b"\x00" * ext.num_blocks * self.block_size)
        else:
            print("Unsupported type = %d" % op.type)
            sys.exit(-1)

        return data

    def dump_part(self, part, update_callback):
        name = part["partition"].partition_name
        out_file = open("%s/%s.img" % (self.out, name), "wb")
        h = hashlib.sha256()

        if self.diff:
            old_file = open("%s/%s.img" % (self.old, name), "rb")
        else:
            old_file = None

        for op in part["operations"]:
            data = self.data_for_op(op, out_file, old_file)
            update_callback(part["partition"].partition_name, 1)

    def list_partitions_info(self):
        partitions_info = []
        for partition in self.dam.partitions:
            size_in_blocks = sum(ext.num_blocks for op in partition.operations for ext in op.dst_extents)
            size_in_bytes = size_in_blocks * self.block_size
            if size_in_bytes >= 1024**3:
                size_str = f"{size_in_bytes / 1024**3:.1f}GB"
            elif size_in_bytes >= 1024**2:
                size_str = f"{size_in_bytes / 1024**2:.1f}MB"
            else:
                size_str = f"{size_in_bytes / 1024:.1f}KB"
            
            partitions_info.append({
                "partition_name": partition.partition_name,
                "size_in_blocks": size_in_blocks,
                "size_in_bytes": size_in_bytes,
                "size_readable": size_str
            })
        
        # Output to JSON file
        output_file = os.path.join(self.out, "partitions_info.json")
        with open(output_file, "w") as f:
            json.dump(partitions_info, f, indent=4)

        # Print to console in a compact format
        readable_info = ', '.join(f"{info['partition_name']}({info['size_readable']})" for info in partitions_info)
        print(readable_info)
        print(f"\nPartition information saved to {output_file}")

    def extract_and_display_metadata(self):
        # Try to extract and display the metadata file from the zip
        metadata_path = "META-INF/com/android/metadata"
        try:
            with zipfile.ZipFile(self.payloadfile, "r") as zip_file:
                with zip_file.open(metadata_path) as meta_file:
                    metadata_content = meta_file.read().decode('utf-8')
                    output_file = os.path.join(self.out, "metadata")
                    with open(output_file, "w") as f:
                        f.write(metadata_content)
                    print(metadata_content)
                    print(f"\nMetadata saved to {output_file}")
        except Exception as e:
            print(f"Failed to extract {metadata_path}: {e}")
