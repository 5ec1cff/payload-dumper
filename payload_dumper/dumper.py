#!/usr/bin/env python
import struct
import hashlib
import bz2
import sys
import argparse
import bsdiff4
import io
import os
from enlighten import get_manager
import lzma
import payload_dumper.update_metadata_pb2 as um

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
    def __init__(self, payloadfile, out, diff=None, old=None, images=""):
        self.payloadfile = payloadfile
        self.out = out
        self.diff = diff
        self.old = old
        self.images = images
        self.validate_magic()
        self.manager = get_manager()

    def run(self):
        if self.images == "":
            progress = self.manager.counter(
                total=len(self.dam.partitions),
                desc="Partitions",
                unit="part",
                position=1,
            )
            for part in self.dam.partitions:
                self.dump_part(part)
                progress.update()
        else:
            images = [image.strip() for image in self.images.split(",")]
            progress = self.manager.counter(
                total=len(images),
                desc="Partitions",
                unit="part",
                position=1,
            )
            for image in images:
                partition = [
                    part for part in self.dam.partitions if part.partition_name == image
                ]
                if partition:
                    self.dump_part(partition[0])
                else:
                    print("Partition %s not found in payload!" % image)
                progress.update()

        self.manager.stop()

    def validate_magic(self):
        magic = self.payloadfile.read(4)
        assert magic == b"CrAU"

        file_format_version = u64(self.payloadfile.read(8))
        assert file_format_version == 2

        manifest_size = u64(self.payloadfile.read(8))

        metadata_signature_size = 0

        if file_format_version > 1:
            metadata_signature_size = u32(self.payloadfile.read(4))

        manifest = self.payloadfile.read(manifest_size)
        self.metadata_signature = self.payloadfile.read(metadata_signature_size)
        self.data_offset = self.payloadfile.tell()

        self.dam = um.DeltaArchiveManifest()
        self.dam.ParseFromString(manifest)
        self.block_size = self.dam.block_size

    def data_for_op(self, op, out_file, old_file):
        self.payloadfile.seek(self.data_offset + op.data_offset)
        data = self.payloadfile.read(op.data_length)

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

    def dump_part(self, part):
        print("Processing %s" % part.partition_name)

        out_file = open("%s/%s.img" % (self.out, part.partition_name), "wb")
        h = hashlib.sha256()

        if self.diff:
            old_file = open("%s/%s.img" % (self.old, part.partition_name), "rb")
        else:
            old_file = None

        operation_progress = self.manager.counter(
            total=len(part.operations), desc="Operations", unit="op", leave=False
        )
        for op in part.operations:
            data = self.data_for_op(op, out_file, old_file)
            operation_progress.update()
        operation_progress.close()


def main():
    parser = argparse.ArgumentParser(description="OTA payload dumper")
    parser.add_argument(
        "payloadfile", type=argparse.FileType("rb"), help="payload file name"
    )
    parser.add_argument(
        "--out", default="output", help="output directory (default: output)"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="extract differential OTA",
    )
    parser.add_argument(
        "--old",
        default="old",
        help="directory with original images for differential OTA (default: old)",
    )
    parser.add_argument(
        "--partitions", default="", help="comma separated list of partitions to extract (default: extract all)"
    )
    args = parser.parse_args()

    # Check for --out directory exists
    if not os.path.exists(args.out):
        os.makedirs(args.out)

    dumper = Dumper(
        args.payloadfile, args.out, diff=args.diff, old=args.old, images=args.partitions
    )
    dumper.run()


if __name__ == "__main__":
    main()
