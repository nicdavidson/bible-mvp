"""Greek edition matching: exact edition names, displaced words (TR«3) included."""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from aligner.sources import SourceToken  # noqa: E402
from backend.word_study import edition_sql, editions_of  # noqa: E402


def test_edition_sql_is_exact_and_keeps_displaced_words():
    conn = sqlite3.connect(":memory:")
    q = f"SELECT {edition_sql('?')}"
    hit = lambda eds, ed: conn.execute(q, (eds, ed)).fetchone()[0]  # noqa: E731
    assert not hit("NA28+NA27+Tyn+SBL+WH+Treg", "TR")       # Treg is not TR
    assert hit("NA28+SBL+WH+Treg+TR+Byz", "TR")
    assert hit("NA28+SBL+Treg+TR«3+Byz«3", "TR")             # in TR, 3 words earlier
    assert hit("NA28+SBL+Treg+TR»1+Byz»1", "Byz")
    assert not hit("NA28+SBL+Treg+TR", "Byz")
    assert editions_of("Treg+TR«3") == {"Treg", "TR"}


def test_aligner_candidates_include_displaced_words():
    tok = SourceToken(pos=5, text="Ἡρῴδης", strong="G2264",
                      editions="NA28+NA27+Tyn+SBL+WH+Treg+TR«3+Byz«3")
    assert tok.in_edition("TR") and tok.in_edition("Byz") and tok.in_edition("SBL")
    treg_only = SourceToken(pos=8, text="ἠρώτων", strong="G2065",
                            editions="NA28+NA27+Tyn+SBL+WH+Treg")
    assert not treg_only.in_edition("TR") and treg_only.in_edition("SBL")


DB = ROOT / "data" / "bible.db"


@pytest.mark.skipif(not DB.exists(), reason="no database")
def test_kjv_interlinear_acts_1_6_has_no_tregelles_only_word():
    from fastapi.testclient import TestClient

    from backend.main import app
    c = TestClient(app)
    kjv = c.get("/api/passage/Acts 1/interlinear", params={"translation": "KJV"}).json()
    bsb = c.get("/api/passage/Acts 1/interlinear", params={"translation": "BSB"}).json()
    # ἠρώτων (position 5) is in NA28/NA27/Tyn/SBL/WH/Treg but not the TR: LIKE '%TR%'
    # used to match 'Treg' and show it in the KJV interlinear.
    kjv6 = {w["position"]: w for w in kjv["verses"]["6"]}
    bsb6 = {w["position"]: w for w in bsb["verses"]["6"]}
    assert set(bsb6) - set(kjv6) == {5}
    assert editions_of(bsb6[5]["editions"]) == {"NA28", "NA27", "Tyn", "SBL", "WH", "Treg"}
    assert all("TR" in editions_of(w["editions"]) for w in kjv6.values())
    # Matt 2:3 'Herod' is displaced in the TR ('Herod the king'), not missing
    mt = c.get("/api/passage/Matthew 2/interlinear", params={"translation": "KJV"}).json()
    assert 5 in {w["position"] for w in mt["verses"]["3"]}
