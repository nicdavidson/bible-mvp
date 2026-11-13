# How a database update reaches a running machine (2026-11)

Branch `v2/search`. Read from `scripts/release_db.py`, `scripts/fetch_db.py`,
`scripts/entrypoint.sh`, `Dockerfile`, `fly.toml`, `fly.dev.toml`, `data/db-manifest.json`
and `.github/workflows/{deploy-dev,promote}.yml`. Nothing was run against Fly.

## Today

| Step | Where | What happens | Peak space needed |
|---|---|---|---|
| 1. Build | crucible | `build_db.py` writes `data/bible.db`; `build_db.py --manifest` stamps version + sha256 into `data/db-manifest.json` | DB + build scratch |
| 2. Release | crucible | `release_db.py <version>` gzips the DB to a temp dir and uploads `<version>/bible.db.gz` + `manifest.json` to the private Tigris bucket (immutable versions). The manifest is committed | DB + gz (~0.4 x DB) |
| 3. CI fetch | GitHub runner, every push to master | `fetch_db.py` downloads the gz, gunzips to `bible.db.tmp`, checks sha256, renames | gz + DB (runner has ~14 GB) |
| 4. Image | Fly remote builder (`flyctl deploy -c fly.dev.toml`) | `COPY data/bible.db data/db-manifest.json data/` puts the DB in its own image layer; code layers follow | image = deps + DB |
| 5. Dev deploy | `bible-mvp-dev` | machine boots the new image (step 7) | see step 7 |
| 6. Prod | `promote.yml` (manual, approval) | `flyctl deploy -c fly.toml --image <dev image>`: the same image, no rebuild | see step 7 |
| 7. Boot | each machine, `entrypoint.sh` as root, before uvicorn | if the image manifest sha differs from `/data/db-manifest.json`: `cp` image DB to `/data/bible.db.tmp` **while the old `/data/bible.db` is still there**, sha256 the copy, `mv` over the old file, write the manifest last | **old DB + new DB + journal on the 1 GB volume** |

Both apps use one `shared-cpu-1x` machine with 1 GB RAM and a 1 GB volume (`bible_data`
at `/data`). The DB is read through `DATABASE_PATH=/data/bible.db`. The volume holds
nothing else of value: user data lives in Supabase, so the volume is a cache of the image's
DB.

### Why it worked at 385 MB

The committed manifest is release `2026.10.02`, 384,897,024 bytes. Step 7 needs
385 + 385 = 770 MB plus a little journal. On a 1 GiB ext4 volume roughly 970 MiB is usable by
root and about 920 MiB by other users (estimate: ext4 defaults reserve ~32 MiB for the journal,
~16 MiB for inode tables and 5% for root; confirm with the `df` command below). 770 MB
fits. The first boot on an empty volume needs only 1 x DB.

### What happens at 850 MB with the old entrypoint

843 MB (this branch) x 2 = 1.7 GB on a ~0.97 GB volume. `cp` fails with ENOSPC, `set -e`
exits, uvicorn never starts and the health check fails. These apps run one machine with a
volume, so a deploy replaces it in place. **The site is down**, the machine retries on
each restart (each attempt refills the disk with a partial `.tmp`, removed at the start of
the next), and the old DB is intact but unused until someone redeploys the previous image.
The integration branch's DB is already 830 MB, so the next release from it would do this.

## Options for an ~850 MB DB

| Option | Volume needed | Restart mid-update | Serve from old DB while updating? | Cost / risk |
|---|---|---|---|---|
| A. Grow the volume, keep the copy | >= 2 x DB + reserve (2 GB volume for 843 MB; 3 GB for growth) | old DB intact; next boot recopies | no (sync runs before the app) | ~$0.15/GB-month; must keep growing with the DB |
| B. Stream from the bucket to the volume, verify, swap | same as A unless combined with C | as A | could, but adds a network dependency at boot | needs Tigris credentials on prod machines; only worth it if the DB leaves the image |
| C. Delete old first when space is short, copy from the image, verify, swap | >= 1 x DB + reserve (~1 GB volume for 843 MB, thin) | volume has no DB and no manifest; next boot copies again from the image (the image is the durable source) | no | brief window with no DB on disk; harmless because the app is not running then |
| D. Read the DB straight from the image (no volume copy) | none for the DB | nothing to repair | n/a | `init_db` opens a writable connection at every boot, which on overlayfs copies the whole 843 MB file up into the writable layer; needs startup to be read-only first, and Fly's rootfs limits checked. A later simplification, not a drop-in |

## Recommendation (implemented): C as a fallback inside A

`scripts/sync_db.py` (called by `entrypoint.sh`) replaces the shell copy:

1. Up to date (volume manifest sha and file size match the image): start immediately.
2. Verify the **source** first: sha256 of the image DB against the image manifest.
   Mismatch: exit 1 with the volume untouched.
3. If the new file fits beside the old one plus a 64 MB reserve: copy to `bible.db.tmp`,
   fsync, check size and sha256, atomic rename, write the manifest last ("side-by-side").
4. Else, if old + free space covers it: delete the volume manifest, then the old DB, then
   step 3 ("delete-first"). Any crash leaves no manifest, so the next boot recopies.
5. Else refuse before deleting anything, with the numbers in the log.

What a reader sees: during any update the machine is restarting (Fly's proxy returns
errors or waits), as today. A partial or unverified DB is never opened, because uvicorn
starts only after the script exits 0. With side-by-side, a crash mid-copy still leaves a
consistent old DB on disk. With delete-first it leaves nothing, and the next boot recopies
from the image in ~5-10 s (the copy plus two sha256 passes; sha256 runs at ~1.7 GB/s on one
N100 core).

Tests (`tests/test_sync_db.py`, simulated volume):
- up to date
- side-by-side
- full volume falls back to delete-first
- refusal when even that cannot fit (old DB untouched)
- image checksum mismatch (volume untouched, even when delete-first would apply)
- ENOSPC mid-copy (old DB kept)
- interrupted copy in both modes, then the next boot completes
- short write caught by the size check
- leftover `.tmp` removed
- empty volume
- stale journal removed

**Smallest safe volume**:
- **Delete-first** (works on today's 1 GB volume for 843 MB, estimated): needs 843 + 64
  = 907 MiB, against ~970 MiB usable. That leaves ~75 MiB free for the app user, which is
  enough for steady state (startup migrations skip on built releases) but thin. A DB over
  ~900 MB will be refused.
- **Side-by-side, with no window without a DB**: 2 x 843 + 64 = 1.75 GiB, so a 2 GB volume.
- **Recommended: 3 GB.** This branch's DB grows by its vectors, and the word-study branch
  changes alignment storage and may drop the commentary search copy, so the size will move.
  3 GB keeps side-by-side mode until the DB passes ~1.4 GB.

## Commands for the owner (not run)

```bash
# 1. Check what is there now
fly volumes list -a bible-mvp
fly volumes list -a bible-mvp-dev
fly ssh console -a bible-mvp -C "df -B1M /data"        # usable MiB on the real volume

# 2. Grow both volumes to 3 GB (online; Fly prints if a machine restart is needed)
fly volumes extend <prod-volume-id> -s 3 -a bible-mvp
fly volumes extend <dev-volume-id>  -s 3 -a bible-mvp-dev
fly ssh console -a bible-mvp -C "df -B1M /data"        # confirm

# 3. Then ship the code with scripts/sync_db.py to dev first (push to master), check
#    the boot log for "[sync_db] ... installed (side-by-side)", then promote.
fly logs -a bible-mvp-dev | grep sync_db
```

`fly.toml` volume settings need no change: the mount is the same; only its size grows.
If growing the volume is not wanted, the new script alone makes an 843 MB release
deployable on the current 1 GB volume (delete-first). The margin is ~60 MB, so keep an eye
on DB size.
