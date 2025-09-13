#!/usr/bin/env python
import bz2
import io
import json
import lzma
import os
import struct
import sys
from zstd import ZSTD_uncompress
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures
from multiprocessing import cpu_count
from functools import partial
import signal

import bsdiff4.core
from enlighten import get_manager

import hashlib
import brotli

from . import mtio
from . import update_metadata_pb2 as um
from .update_metadata_pb2 import InstallOperation
from .ziputil import get_zip_stored_entry_offset
from .future_util import CombinedFuture, wait_interruptible


def u32(x):
    return struct.unpack(">I", x)[0]


def u64(x):
    return struct.unpack(">Q", x)[0]

BSDF2_MAGIC = b'BSDF2'

def bsdf2_decompress(alg, data):
    if alg == 0:
        return data
    elif alg == 1:
        return bz2.decompress(data)
    elif alg == 2:
        return brotli.decompress(data)
    else:
        raise ValueError(f'unknown algorithm {alg}')


# Adapted from bsdiff4.read_patch
def bsdf2_read_patch(fi):
    """read a bsdiff/BSDF2-format patch from stream 'fi'
    """
    magic = fi.read(8)
    if magic == bsdiff4.format.MAGIC:
        # bsdiff4 uses bzip2 (algorithm 1)
        alg_control = alg_diff = alg_extra = 1
    elif magic[:5] == BSDF2_MAGIC:
        alg_control = magic[5]
        alg_diff = magic[6]
        alg_extra = magic[7]
    else:
        raise ValueError("incorrect magic bsdiff/BSDF2 header")

    # length headers
    len_control = bsdiff4.core.decode_int64(fi.read(8))
    len_diff = bsdiff4.core.decode_int64(fi.read(8))
    len_dst = bsdiff4.core.decode_int64(fi.read(8))

    # read the control header
    bcontrol = bsdf2_decompress(alg_control, fi.read(len_control))
    tcontrol = [(bsdiff4.core.decode_int64(bcontrol[i:i + 8]),
                 bsdiff4.core.decode_int64(bcontrol[i + 8:i + 16]),
                 bsdiff4.core.decode_int64(bcontrol[i + 16:i + 24]))
                for i in range(0, len(bcontrol), 24)]

    # read the diff and extra blocks
    bdiff = bsdf2_decompress(alg_diff, fi.read(len_diff))
    bextra = bsdf2_decompress(alg_extra, fi.read())
    return len_dst, tcontrol, bdiff, bextra


class Dumper:
    def __init__(
        self, payloadfile, out, diff=None, old=None, images="", workers=cpu_count(), list_partitions=False, extract_metadata=False
    ):
        self.payloadfile: mtio.MTIOBase = payloadfile
        self.manager = get_manager()
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
                off, size = get_zip_stored_entry_offset(self.payloadfile, 'payload.bin')
                #print(f'payload.bin in zip {off=} {size=}')
                self.base_off = off
            except:
                #from traceback import print_exc
                #print_exc()
                #print('not a zip')
                self.base_off = 0

            self.parse_metadata()

            if self.list_partitions:
                self.list_partitions_info()

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
                operations.append(
                    {
                        "operation": operation,
                        "offset": self.data_offset + operation.data_offset,
                        "length": operation.data_length,
                    }
                )
            partitions_with_ops.append(
                {
                    "partition": partition,
                    "operations": operations,
                }
            )

        self.multiprocess_partitions(partitions_with_ops)
        self.manager.stop()
        self.payloadfile.close()
        # make progressbar not overlaid by shell prompt
        print()

    def multiprocess_partitions(self, partitions):
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for part in partitions:
                try:
                    partition_name = part["partition"].partition_name
                    bar = self.manager.counter(
                        total=len(part["operations"]),
                        desc=f"{partition_name}",
                        unit="ops",
                    )

                    out_file = mtio.MTFile("%s/%s.img" % (self.out, partition_name), "w")

                    if self.diff:
                        old_file = mtio.MTFile("%s/%s.img" % (self.old, partition_name), "rb")
                    else:
                        old_file = None

                    ops = part['operations']
                    tasks = []
                    for op in ops:
                        tasks.append(
                            executor.submit(
                                self.do_op,
                                partition_name,
                                op,
                                out_file, old_file, bar
                            )
                        )

                    dones, _ = wait_interruptible(tasks, return_when=futures.FIRST_EXCEPTION)
                    for t in dones:
                        e = t.exception(0)
                        if e is not None:
                            raise e

                    out_file.close()
                    if old_file is not None:
                        old_file.close()
                    bar.close()
                except KeyboardInterrupt:
                    try:
                        bar.close()
                        self.manager.stop()
                    except:
                        pass
                    print('Stopping ...')
                    if sys.platform == 'win32':
                        os.kill(os.getpid(), signal.CTRL_BREAK_EVENT)
                    else:
                        os.kill(os.getpid(), signal.SIGKILL)
                    sys.exit(1)


    def parse_metadata(self):
        head_len = 4 + 8 + 8 + 4
        fp = self.base_off
        buffer = self.payloadfile.read(fp, head_len)
        fp += head_len
        assert len(buffer) == head_len
        magic = buffer[:4]
        assert magic == b"CrAU"

        file_format_version = u64(buffer[4:12])
        assert file_format_version == 2

        manifest_size = u64(buffer[12:20])

        metadata_signature_size = 0

        if file_format_version > 1:
            metadata_signature_size = u32(buffer[20:24])

        manifest = self.payloadfile.read(fp, manifest_size)
        fp += manifest_size
        self.metadata_signature = self.payloadfile.read(fp, metadata_signature_size)
        fp += metadata_signature_size
        self.data_offset = fp - self.base_off
        self.dam = um.DeltaArchiveManifest()
        self.dam.ParseFromString(manifest)
        self.block_size = self.dam.block_size

    def data_for_op(self, operation, out_file: mtio.MTIOBase, old_file: mtio.MTIOBase):
        offset = operation["offset"]
        length = operation["length"]
        op = operation["operation"]
        op: InstallOperation

        data = self.payloadfile.read(self.base_off + offset, length)

        if op.data_sha256_hash:
            assert hashlib.sha256(data).digest() == op.data_sha256_hash, 'operation data hash mismatch'

        if op.type == InstallOperation.REPLACE_XZ:
            dec = lzma.LZMADecompressor()
            data = dec.decompress(data)
            assert op.dst_extents[0].num_blocks * self.block_size == len(data)
            out_file.write(op.dst_extents[0].start_block * self.block_size, data)
        elif op.type == InstallOperation.REPLACE_BZ:
            dec = bz2.BZ2Decompressor()
            data = dec.decompress(data)
            assert op.dst_extents[0].num_blocks * self.block_size == len(data)
            out_file.write(op.dst_extents[0].start_block * self.block_size, data)
        elif op.type == InstallOperation.REPLACE:
            out_file.write(op.dst_extents[0].start_block * self.block_size, data)
        elif op.type == InstallOperation.SOURCE_COPY:
            if not self.diff:
                print("SOURCE_COPY supported only for differential OTA")
                sys.exit(-2)
            for ext in op.src_extents:
                data = old_file.read(ext.start_block * self.block_size, ext.num_blocks * self.block_size)
                out_file.write(op.dst_extents[0].start_block * self.block_size, data)
        elif op.type in (InstallOperation.SOURCE_BSDIFF, InstallOperation.BROTLI_BSDIFF):
            if not self.diff:
                print("SOURCE_BSDIFF supported only for differential OTA")
                sys.exit(-3)
            tmp_buff = io.BytesIO()
            for ext in op.src_extents:
                old_data = old_file.read(ext.start_block * self.block_size, ext.num_blocks * self.block_size)
                tmp_buff.write(old_data)
            tmp_buff.seek(0)
            old_data = tmp_buff.read()
            tmp_buff.seek(0)
            tmp_buff.write(bsdiff4.core.patch(old_data, *bsdf2_read_patch(io.BytesIO(data))))
            n = 0
            tmp_buff.seek(0)
            for ext in InstallOperation.dst_extents:
                tmp_buff.seek(n * self.block_size)
                n += ext.num_blocks
                data = tmp_buff.read(ext.num_blocks * self.block_size)
                out_file.write(ext.start_block * self.block_size, data)
        elif op.type == InstallOperation.ZERO:
            for ext in op.dst_extents:
                out_file.write(ext.start_block * self.block_size, b"\x00" * ext.num_blocks * self.block_size)
        elif op.type == InstallOperation.ZSTD:
            data = ZSTD_uncompress(data)
            assert op.dst_extents[0].num_blocks * self.block_size == len(data)
            out_file.write(op.dst_extents[0].start_block * self.block_size, data)
        else:
            raise ValueError("Unsupported type = %d" % op.type)

    def do_op(self, partition_name, op, out_file, old_file, bar):
        #print('do op', partition_name, op)
        try:
            self.data_for_op(op, out_file, old_file)
            bar.update(1)
        except futures.CancelledError:
            pass

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
                "size_readable": size_str,
                "hash": partition.new_partition_info.hash.hex()
            })
        
        # Output to JSON file
        output_file = os.path.join(self.out, "partitions_info.json")
        with open(output_file, "w") as f:
            json.dump(partitions_info, f, indent=4)

        # Print to console in a compact format
        readable_info = '\n'.join(f"{info['partition_name']}({info['size_readable']})" for info in partitions_info)
        print(f'Total {len(partitions_info)} partitions')
        print(readable_info)
        print(f"\nPartition information saved to {output_file}")

    def extract_and_display_metadata(self):
        # Try to extract and display the metadata file from the zip
        metadata_path = "META-INF/com/android/metadata"
        try:
            off, sz = get_zip_stored_entry_offset(self.payloadfile, metadata_path)
            data = self.payloadfile.read(off, sz)
            output_file = os.path.join(self.out, "metadata")
            with open(output_file, "wb") as f:
                f.write(data)
            print(data.decode('utf-8'))
            print(f"\nMetadata saved to {output_file}")
        except Exception as e:
            print(f"Failed to extract {metadata_path}: {e}")
