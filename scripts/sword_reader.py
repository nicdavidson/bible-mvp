"""
Minimal reader for CrossWire SWORD commentary modules (zCom, zCom4, RawCom, RawCom4).

Only what the commentary importers need: walk every verse slot of a module in
KJV versification and return the raw (ThML/OSIS) text stored there, grouping
"linked" verses (several verse slots that point at the same stored text, which
is how SWORD encodes a comment on a verse range) into one entry.

SWORD index layout per testament file (ot.* / nt.*), KJV versification:
    slot 0          module header (unused)
    slot 1          testament heading
    per book:       1 slot for the book introduction (chapter 0, verse 0)
    per chapter:    1 slot for the chapter introduction (verse 0), then verses 1..n

File formats (little endian):
    RawCom  : <t>.vss = (u32 offset, u16 size) per slot, data in <t>
    RawCom4 : <t>.vss = (u32 offset, u32 size) per slot, data in <t>
    zCom    : <t>.czv = (u32 block, u32 offset, u16 size) per slot
              <t>.czs = (u32 offset, u32 csize, u32 usize) per block, blocks in <t>.czz (zlib)
    zCom4   : like zCom but <t>.czv slots are (u32 block, u32 offset, u32 size)

No third-party dependencies (pysword is GPL and not installed here).
"""
from __future__ import annotations

import configparser
import struct
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

# OSIS book ids in KJV order -> names used in the `books` table
OSIS_BOOKS = [
    ("Gen", "Genesis"), ("Exod", "Exodus"), ("Lev", "Leviticus"), ("Num", "Numbers"),
    ("Deut", "Deuteronomy"), ("Josh", "Joshua"), ("Judg", "Judges"), ("Ruth", "Ruth"),
    ("1Sam", "1 Samuel"), ("2Sam", "2 Samuel"), ("1Kgs", "1 Kings"), ("2Kgs", "2 Kings"),
    ("1Chr", "1 Chronicles"), ("2Chr", "2 Chronicles"), ("Ezra", "Ezra"),
    ("Neh", "Nehemiah"), ("Esth", "Esther"), ("Job", "Job"), ("Ps", "Psalms"),
    ("Prov", "Proverbs"), ("Eccl", "Ecclesiastes"), ("Song", "Song of Solomon"),
    ("Isa", "Isaiah"), ("Jer", "Jeremiah"), ("Lam", "Lamentations"), ("Ezek", "Ezekiel"),
    ("Dan", "Daniel"), ("Hos", "Hosea"), ("Joel", "Joel"), ("Amos", "Amos"),
    ("Obad", "Obadiah"), ("Jonah", "Jonah"), ("Mic", "Micah"), ("Nah", "Nahum"),
    ("Hab", "Habakkuk"), ("Zeph", "Zephaniah"), ("Hag", "Haggai"), ("Zech", "Zechariah"),
    ("Mal", "Malachi"),
    ("Matt", "Matthew"), ("Mark", "Mark"), ("Luke", "Luke"), ("John", "John"),
    ("Acts", "Acts"), ("Rom", "Romans"), ("1Cor", "1 Corinthians"),
    ("2Cor", "2 Corinthians"), ("Gal", "Galatians"), ("Eph", "Ephesians"),
    ("Phil", "Philippians"), ("Col", "Colossians"), ("1Thess", "1 Thessalonians"),
    ("2Thess", "2 Thessalonians"), ("1Tim", "1 Timothy"), ("2Tim", "2 Timothy"),
    ("Titus", "Titus"), ("Phlm", "Philemon"), ("Heb", "Hebrews"), ("Jas", "James"),
    ("1Pet", "1 Peter"), ("2Pet", "2 Peter"), ("1John", "1 John"), ("2John", "2 John"),
    ("3John", "3 John"), ("Jude", "Jude"), ("Rev", "Revelation"),
]
OSIS_TO_NAME = dict(OSIS_BOOKS)


@dataclass
class SwordEntry:
    book: str            # name as in the books table
    chapter: int         # 0 = book introduction
    verse_start: int     # 0 = chapter (or book) introduction
    verse_end: int
    raw: str             # ThML / OSIS fragment as stored


def kjv_versification(conn) -> dict[str, list[int]]:
    """Verse counts per chapter for each book, read from the KJV text in the DB.

    SWORD's KJV versification has the same 31,102 verses as the KJV we import.
    """
    rows = conn.execute(
        "SELECT book, chapter, MAX(verse) FROM verses WHERE translation_id = 'KJV' "
        "GROUP BY book, chapter"
    ).fetchall()
    v11n: dict[str, list[int]] = {}
    for book, chapter, maxv in rows:
        chapters = v11n.setdefault(book, [])
        while len(chapters) < chapter:
            chapters.append(0)
        chapters[chapter - 1] = maxv
    total = sum(sum(c) for c in v11n.values())
    if total != 31102 or len(v11n) != 66:
        raise RuntimeError(f"KJV versification incomplete in DB ({len(v11n)} books, {total} verses)")
    return v11n


class SwordModule:
    def __init__(self, zip_path: Path):
        self.zf = zipfile.ZipFile(zip_path)
        conf_name = next(n for n in self.zf.namelist() if n.startswith("mods.d/") and n.endswith(".conf"))
        raw_conf = self.zf.read(conf_name).decode("utf-8", errors="replace")
        # conf files are INI-like but allow continuation lines ending in "\"
        raw_conf = raw_conf.replace("\\\n", " ")
        cp = configparser.ConfigParser(strict=False, interpolation=None, comment_prefixes=("#",))
        cp.optionxform = str
        cp.read_string(raw_conf)
        self.name = cp.sections()[0]
        self.conf = dict(cp[self.name])
        self.driver = self.conf["ModDrv"]
        self.encoding = "utf-8" if self.conf.get("Encoding", "").upper() == "UTF-8" else "latin-1"
        v11n = self.conf.get("Versification", "KJV")
        if v11n != "KJV":
            raise NotImplementedError(f"{self.name}: versification {v11n} not supported")
        data_path = self.conf["DataPath"].lstrip("./").rstrip("/") + "/"
        self.data_path = data_path
        self._block_cache: dict[tuple[str, int], bytes] = {}

    def _read(self, name: str) -> bytes | None:
        try:
            return self.zf.read(self.data_path + name)
        except KeyError:
            return None

    def _slots(self, testament: str):
        """Yield (key, text_bytes_getter) per slot; key identifies the stored text."""
        drv = self.driver
        if drv in ("RawCom", "RawCom4"):
            idx = self._read(f"{testament}.vss")
            data = self._read(testament)
            if idx is None or data is None:
                return []
            fmt, size = ("<IH", 6) if drv == "RawCom" else ("<II", 8)
            out = []
            for i in range(len(idx) // size):
                off, ln = struct.unpack_from(fmt, idx, i * size)
                out.append(((off, ln), data[off:off + ln] if ln else b""))
            return out
        if drv in ("zCom", "zCom4"):
            # commentary modules use .cz?; some older ones ship Bible-style .bz? names
            vidx = self._read(f"{testament}.czv") or self._read(f"{testament}.bzv")
            bidx = self._read(f"{testament}.czs") or self._read(f"{testament}.bzs")
            data = self._read(f"{testament}.czz") or self._read(f"{testament}.bzz")
            if vidx is None or bidx is None or data is None:
                return []
            fmt, size = ("<IIH", 10) if drv == "zCom" else ("<III", 12)
            blocks = {}

            def block(n):
                if n not in blocks:
                    off, csize, _usize = struct.unpack_from("<III", bidx, n * 12)
                    blocks[n] = zlib.decompress(data[off:off + csize])
                return blocks[n]

            out = []
            for i in range(len(vidx) // size):
                bn, off, ln = struct.unpack_from(fmt, vidx, i * size)
                text = block(bn)[off:off + ln] if ln else b""
                out.append(((bn, off, ln), text))
            return out
        raise NotImplementedError(f"{self.name}: driver {drv} not supported")

    def entries(self, v11n: dict[str, list[int]], include_intros: bool = False):
        """Yield SwordEntry objects in canonical order, linked verses merged into ranges."""
        for testament, books in (("ot", OSIS_BOOKS[:39]), ("nt", OSIS_BOOKS[39:])):
            slots = self._slots(testament)
            if not slots:
                continue
            i = 2  # skip module header + testament heading
            for _osis, name in books:
                chapters = v11n[name]
                key, text = slots[i]
                if include_intros and text.strip():
                    yield SwordEntry(name, 0, 0, 0, text.decode(self.encoding, errors="replace"))
                i += 1
                for ch, nverses in enumerate(chapters, start=1):
                    key, text = slots[i]
                    if include_intros and text.strip():
                        yield SwordEntry(name, ch, 0, 0, text.decode(self.encoding, errors="replace"))
                    i += 1
                    prev_key = None
                    cur = None
                    for v in range(1, nverses + 1):
                        key, text = slots[i]
                        i += 1
                        if not key[-1]:  # empty slot
                            if cur:
                                yield cur
                                cur = None
                            prev_key = None
                            continue
                        if key == prev_key and cur is not None:
                            cur.verse_end = v  # linked verse: same stored text
                            continue
                        if cur:
                            yield cur
                        cur = SwordEntry(name, ch, v, v, text.decode(self.encoding, errors="replace"))
                        prev_key = key
                    if cur:
                        yield cur
            if i != len(slots):
                # Trailing slots are normal in some modules (padding); only warn on shortfall.
                if i > len(slots):
                    raise RuntimeError(f"{self.name}/{testament}: index shorter than KJV v11n")


def read_conf(zip_path: Path) -> dict:
    return SwordModule(zip_path).conf


if __name__ == "__main__":
    import sqlite3
    import sys
    import os

    db = os.environ.get("DATABASE_PATH", str(Path(__file__).parent.parent / "data" / "bible.db"))
    conn = sqlite3.connect(db)
    v = kjv_versification(conn)
    mod = SwordModule(Path(sys.argv[1]))
    n = 0
    for e in mod.entries(v, include_intros="--intros" in sys.argv):
        n += 1
        if n <= int(os.environ.get("SHOW", "3")):
            print(e.book, e.chapter, e.verse_start, e.verse_end, repr(e.raw[:300]))
    print(mod.name, mod.driver, "entries:", n)
