"""Publish data/bible.db as a versioned content release to the Tigris bucket.

    python scripts/build_db.py --manifest      # stamps version + sha into data/db-manifest.json
    set -a; . ~/.config/bible-mvp/tigris.env; set +a   # on crucible
    python scripts/release_db.py 2026.10.02

The version must match the manifest. Commit the manifest; CI's fetch_db.py pulls that
release into the image, so dev gets it on push and prod on promote.
Releases are immutable: re-using a version name is refused.
"""
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import boto3

DB = Path(__file__).resolve().parent.parent / "data" / "bible.db"


def main(version: str) -> None:
    manifest_version = json.loads((DB.with_name("db-manifest.json")).read_text())["version"]
    if version != manifest_version:
        sys.exit(f"version {version} != db-manifest.json version {manifest_version}; run build_db.py --manifest")
    s3, bucket = boto3.client("s3"), os.environ["BUCKET_NAME"]
    if s3.list_objects_v2(Bucket=bucket, Prefix=f"{version}/").get("KeyCount"):
        sys.exit(f"release {version} already exists; pick a new version")

    sha = hashlib.sha256()
    with open(DB, "rb") as f:
        while chunk := f.read(1 << 20):
            sha.update(chunk)
    manifest = {
        "version": version,
        "sha256": sha.hexdigest(),
        "size": DB.stat().st_size,
        "released": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with tempfile.TemporaryDirectory() as tmp:
        gz = Path(tmp) / "bible.db.gz"
        with open(DB, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        print(f"uploading {gz.stat().st_size / 1e6:.0f} MB compressed...")
        s3.upload_file(str(gz), bucket, f"{version}/bible.db.gz")
    s3.put_object(Bucket=bucket, Key=f"{version}/manifest.json", Body=json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
