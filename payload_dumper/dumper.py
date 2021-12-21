#!/usr/bin/env python
from time import sleep
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
from multiprocessing import Process, Queue, cpu_count
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
    def __init__(
        self, payloadfile, out, diff=None, old=None, images="", workers=cpu_count()
    ):
        self.payloadfile = payloadfile
        self.out = out
        self.diff = diff
        self.old = old
        self.images = images
        self.workers = workers
        self.validate_magic()
        self.manager = get_manager()

    def run(self):
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
        started = 0
        active = {}
        pb_started = self.manager.counter(
            total=len(partitions), desc="Partitions", unit="part", color="yellow"
        )
        pb_finished = pb_started.add_subcounter("green", all_fields=True)

        while len(partitions) > started or active:

            if len(partitions) > started and len(active) < self.workers:
                queue = Queue()
                part = partitions[started]
                process = Process(target=self.dump_part, args=(part, queue))
                started += 1
                counter = self.manager.counter(
                    total=len(part["operations"]),
                    desc="    %s" % part["partition"].partition_name,
                    unit="ops",
                    leave=False,
                )
                process.start()
                pb_started.update()
                active[started] = (process, queue, counter)

            for partition in tuple(active.keys()):
                process, queue, counter = active[partition]
                alive = process.is_alive()

                count = None
                while not queue.empty():
                    count = queue.get()

                if count is not None:
                    counter.count = count
                    counter.update(0)

                if not alive:
                    counter.close()
                    print(
                        "%s - processed %d operations"
                        % (
                            partitions[partition - 1]["partition"].partition_name,
                            counter.total,
                        )
                    )
                    del active[partition]
                    pb_finished.update_from(pb_started)

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

    def dump_part(self, part, queue):
        name = part["partition"].partition_name
        out_file = open("%s/%s.img" % (self.out, name), "wb")
        h = hashlib.sha256()

        if self.diff:
            old_file = open("%s/%s.img" % (self.old, name), "rb")
        else:
            old_file = None

        i = 0
        for op in part["operations"]:
            data = self.data_for_op(op, out_file, old_file)
            i += 1
            queue.put(i)


def main():
    parser = argparse.ArgumentParser(description="OTA payload dumper")
    parser.add_argument(
        "payloadfile", type=argparse.FileType("rb"), help="payload file name"
    )
    parser.add_argument(
        "--out", default="output", help="output directory (default: 'output')"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="extract differential OTA",
    )
    parser.add_argument(
        "--old",
        default="old",
        help="directory with original images for differential OTA (default: 'old')",
    )
    parser.add_argument(
        "--partitions",
        default="",
        help="comma separated list of partitions to extract (default: extract all)",
    )
    parser.add_argument(
        "--workers",
        default=cpu_count(),
        type=int,
        help="numer of workers (default: CPU count - %d)" % cpu_count(),
    )
    args = parser.parse_args()

    # Check for --out directory exists
    if not os.path.exists(args.out):
        os.makedirs(args.out)

    dumper = Dumper(
        args.payloadfile,
        args.out,
        diff=args.diff,
        old=args.old,
        images=args.partitions,
        workers=args.workers,
    )
    dumper.run()


if __name__ == "__main__":
    main()
