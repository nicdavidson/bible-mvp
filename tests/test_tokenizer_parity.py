"""The reader UI and the alignment build must number words identically.

english_word_alignments is keyed by word position, so if formatVerseText() in
frontend/static/js/app.js and scripts/aligner/text.py ever disagree, every link
after the first differing word in a verse points at the wrong word. Both sides
are checked against the same vectors: tests/fixtures/tokenizer_vectors.json
(edge cases plus ~320 verses each of BSB, KJV and WEB, many with curly quotes,
apostrophes and dashes). Regenerate the vectors only on purpose, together with
a change to both tokenizers and an alignment rebuild.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aligner.text import tappable_words  # noqa: E402

VECTORS = ROOT / "tests" / "fixtures" / "tokenizer_vectors.json"


def test_vectors_cover_each_translation():
    refs = [v["ref"].split()[0] for v in json.loads(VECTORS.read_text())]
    for tr in ("BSB", "KJV", "WEB"):
        assert refs.count(tr) >= 250


def test_python_tokenizer_matches_vectors():
    for v in json.loads(VECTORS.read_text()):
        assert tappable_words(v["text"]) == v["words"], v["ref"]


def test_quoted_speech_words_are_tappable():
    words = tappable_words("And God said, “Let there be light,” and there was light.")
    assert words[3:7] == ["Let", "there", "be", "light"]
    assert tappable_words("“Truly, truly, I tell you—again.”") == [
        "Truly", "truly", "I", "tell", "you", "again"]
    assert tappable_words("God’s bless'd Beth-el") == ["God’s", "bless'd", "Beth-el"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_tokenizer_matches_vectors():
    r = subprocess.run(
        ["node", str(ROOT / "tests" / "js" / "tokenize_parity.mjs"),
         str(ROOT / "frontend" / "static" / "js" / "app.js"), str(VECTORS)],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
