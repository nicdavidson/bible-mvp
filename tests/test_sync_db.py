"""scripts/sync_db.py: installing the image DB onto a small volume (simulated)."""
import errno
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import sync_db  # noqa: E402

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def small_reserve(monkeypatch):
    monkeypatch.setattr(sync_db, "RESERVE", 1 * MB)


def make_release(d: Path, version: str, size: int, seed: int):
    d.mkdir(parents=True, exist_ok=True)
    data = hashlib.sha256(str(seed).encode()).digest() * (size // 32)
    (d / "bible.db").write_bytes(data)
    m = {"version": version, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    (d / "db-manifest.json").write_text(json.dumps(m))
    return m


@pytest.fixture
def env(tmp_path):
    image, vol = tmp_path / "image", tmp_path / "volume"
    new = make_release(image, "2026.11.13", 8 * MB, seed=2)
    old = make_release(vol, "2026.10.02", 4 * MB, seed=1)
    return {"image": image, "vol": vol, "new": new, "old": old}


def run(env, free_mb, **kw):
    return sync_db.sync(env["image"] / "bible.db", env["image"] / "db-manifest.json",
                        env["vol"] / "bible.db", env["vol"] / "db-manifest.json",
                        free=lambda d: free_mb * MB, **kw)


def volume_state(env):
    db, man = env["vol"] / "bible.db", env["vol"] / "db-manifest.json"
    sha = hashlib.sha256(db.read_bytes()).hexdigest() if db.exists() else None
    m = json.loads(man.read_text()) if man.exists() else None
    tmp = (env["vol"] / "bible.db.tmp").exists()
    return sha, (m or {}).get("sha256"), tmp


def test_up_to_date_is_a_no_op(env):
    assert run(env, 100) == "side-by-side"
    assert run(env, 100) == "up-to-date"


def test_side_by_side_when_room(env):
    assert run(env, 20) == "side-by-side"
    assert volume_state(env) == (env["new"]["sha256"], env["new"]["sha256"], False)


def test_full_volume_falls_back_to_delete_first(env):
    # 5 MB free: new (8) + reserve (1) does not fit beside old (4), but does after deleting it
    assert run(env, 5) == "delete-first"
    assert volume_state(env) == (env["new"]["sha256"], env["new"]["sha256"], False)


def test_refuses_when_even_delete_first_cannot_fit(env):
    with pytest.raises(SystemExit) as e:
        run(env, 2)  # 2 free + 4 old < 8 + 1
    assert e.value.code == 1
    assert volume_state(env) == (env["old"]["sha256"], env["old"]["sha256"], False)


def test_checksum_mismatch_in_image_leaves_volume_untouched(env):
    m = json.loads((env["image"] / "db-manifest.json").read_text())
    m["sha256"] = "0" * 64
    (env["image"] / "db-manifest.json").write_text(json.dumps(m))
    with pytest.raises(SystemExit):
        run(env, 5)  # would be delete-first: must not delete anything
    assert volume_state(env) == (env["old"]["sha256"], env["old"]["sha256"], False)


class FailingWriter:
    """File opener whose writes fail (ENOSPC) or crash (interrupt) after N bytes."""

    def __init__(self, after: int, exc):
        self.after, self.exc, self.written = after, exc, 0

    def __call__(self, path, mode):
        outer = self
        real = open(path, mode)

        class W:
            def write(self, b):
                if outer.written + len(b) > outer.after:
                    raise outer.exc
                outer.written += len(b)
                return real.write(b)

            def __getattr__(self, name):
                return getattr(real, name)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                real.close()
        return W()


def test_disk_full_during_side_by_side_copy_keeps_old_db(env):
    full = OSError(errno.ENOSPC, "No space left on device")
    with pytest.raises(SystemExit):
        run(env, 20, opener=FailingWriter(3 * MB, full))
    assert volume_state(env) == (env["old"]["sha256"], env["old"]["sha256"], False)


def test_interrupted_copy_side_by_side_then_next_boot_completes(env):
    with pytest.raises(KeyboardInterrupt):  # stands in for SIGKILL / power loss mid-copy
        run(env, 20, opener=FailingWriter(5 * MB, KeyboardInterrupt()))
    # old DB + old manifest still consistent: the app could start on it
    assert volume_state(env)[:2] == (env["old"]["sha256"], env["old"]["sha256"])
    assert run(env, 20) == "side-by-side"
    assert volume_state(env) == (env["new"]["sha256"], env["new"]["sha256"], False)


def test_interrupted_copy_delete_first_then_next_boot_recovers(env):
    with pytest.raises(KeyboardInterrupt):
        run(env, 5, opener=FailingWriter(5 * MB, KeyboardInterrupt()))
    sha, man, _ = volume_state(env)
    assert man is None  # no manifest: next boot must copy again, never "up to date"
    assert sha is None  # old DB was deleted, new one never renamed into place
    assert run(env, 13) in ("side-by-side", "delete-first")
    assert volume_state(env) == (env["new"]["sha256"], env["new"]["sha256"], False)


def test_short_write_is_caught_by_size_check(env):
    # The hash covers what was read; a device that silently drops bytes is caught by size.
    class Short(FailingWriter):
        def __call__(self, path, mode):
            real = open(path, mode)

            class W:
                def write(self, b):
                    return real.write(b[:-1])

                def __getattr__(self, name):
                    return getattr(real, name)

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    real.close()
            return W()

    with pytest.raises(SystemExit):
        run(env, 20, opener=Short(0, None))
    assert volume_state(env) == (env["old"]["sha256"], env["old"]["sha256"], False)


def test_leftover_tmp_from_crash_is_removed(env):
    (env["vol"] / "bible.db.tmp").write_bytes(b"x" * MB)
    assert run(env, 20) == "side-by-side"
    assert not (env["vol"] / "bible.db.tmp").exists()


def test_first_boot_empty_volume(env):
    (env["vol"] / "bible.db").unlink()
    (env["vol"] / "db-manifest.json").unlink()
    assert run(env, 9) == "side-by-side"
    assert volume_state(env)[0] == env["new"]["sha256"]


def test_stale_journal_removed(env):
    (env["vol"] / "bible.db-journal").write_bytes(b"j")
    run(env, 20)
    assert not (env["vol"] / "bible.db-journal").exists()
