# -*- coding: utf-8 -*-
"""Sync an OpenNeuro dataset from its public S3 bucket (unsigned).

Usage: python fetch_openneuro_s3.py <dsid> <dest_dir>
Skips files already present with matching size; prints a summary and
appends a sha-less size journal (S3 ETags are not sha256; integrity is
size + BIDS validation downstream).
"""
import os
import sys

import boto3
from botocore import UNSIGNED
from botocore.config import Config


def main():
    dsid, dest = sys.argv[1], sys.argv[2]
    s3 = boto3.client("s3", config=Config(
        signature_version=UNSIGNED, retries={"max_attempts": 10}))
    total = done = skipped = 0
    for page in s3.get_paginator("list_objects_v2").paginate(
            Bucket="openneuro.org", Prefix=dsid + "/"):
        for o in page.get("Contents", []):
            key, size = o["Key"], o["Size"]
            rel = key[len(dsid) + 1:]
            if not rel:
                continue
            path = os.path.join(dest, rel)
            total += 1
            if os.path.exists(path) and os.path.getsize(path) == size:
                skipped += 1
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            s3.download_file("openneuro.org", key, path)
            done += 1
            if done % 50 == 0:
                print(f"  {done} downloaded / {skipped} skipped "
                      f"/ {total} listed")
    print(f"{dsid}: {done} downloaded, {skipped} already present, "
          f"{total} total")


if __name__ == "__main__":
    main()
