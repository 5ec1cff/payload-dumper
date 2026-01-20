#!/usr/bin/env python3
import argparse
import os
from multiprocessing import cpu_count

from . import http_file
from .dumper import Dumper
from . import mtio

def main():
    parser = argparse.ArgumentParser(description="OTA payload dumper")
    parser.add_argument("payloadfile", help="payload file name")
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
        help="number of workers (default: CPU count - %d)" % cpu_count(),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list partitions in the payload file",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="change '--list' behavior to only print partition names, no create files and directory in current work directory.",
    )
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="extract and display metadata file from the payload",
    )
    parser.add_argument("--header", action="append", nargs=2)
    args = parser.parse_args()

    output_files = (not args.no_output) if args.list else True
    # Check for --out directory exists
    if (not os.path.exists(args.out)) and output_files:
        os.makedirs(args.out)

    payload_file = args.payloadfile
    if payload_file.startswith("http://") or payload_file.startswith("https://"):
        headers = None
        if args.header is not None:
            headers = {}
            for k, v in args.header:
                headers[k] = v
        payload_file = http_file.HttpRangeFileMTIO(payload_file, headers=headers)
    else:
        payload_file = mtio.MTFile(payload_file, "r")
    dumper = Dumper(
        payload_file,
        args.out,
        diff=args.diff,
        old=args.old,
        images=args.partitions,
        workers=args.workers,
        list_partitions=args.list,
        extract_metadata=args.metadata,
        output_files=output_files
    )

    dumper.run()

    if isinstance(payload_file, http_file.HttpRangeFileMTIO):
        print("\ntotal bytes read from network:", payload_file.transferred_bytes)
