"""Download the DB release pinned in data/db-manifest.json into data/bible.db.

Used by CI before `fly deploy` (bible.db isn't in git). Releases live in a private
Tigris bucket, uploaded by scripts/release_db.py; needs the AWS_* + BUCKET_NAME env.
No-op when data/bible.db already matches the manifest sha.
"""
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import boto3

DATA = Path(__file__).resolve().parent.parent / "data"
DB = DATA / "bible.db"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = json.loads((DATA / "db-manifest.json").read_text())
    version, want = manifest["version"], manifest["sha256"]
    if DB.exists() and sha256(DB) == want:
        print(f"[fetch_db] {version} already present")
        return

    gz, tmp = DATA / "bible.db.gz.tmp", DATA / "bible.db.tmp"
    print(f"[fetch_db] downloading {version}...")
    boto3.client("s3").download_file(os.environ["BUCKET_NAME"], f"{version}/bible.db.gz", str(gz))
    with gzip.open(gz, "rb") as src, open(tmp, "wb") as dst:
        while chunk := src.read(1 << 20):
            dst.write(chunk)
    gz.unlink()
    if sha256(tmp) != want:
        tmp.unlink()
        sys.exit(f"[fetch_db] sha256 mismatch for {version}")
    tmp.replace(DB)
    print(f"[fetch_db] {version} installed")


if __name__ == "__main__":
    main()
