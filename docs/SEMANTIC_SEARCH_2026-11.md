# Meaning search (2026-11)

Branch `v2/search`. Adds search by meaning over Bible verses, so "where does Scripture talk
about waiting on God" finds Isaiah 40:31 without the reader typing its words, plus "more
like this verse". It finds and ranks existing verses. It never writes text.

## Results in brief

Measured 2026-11-13 on `bridge` (N100, 4 cores, shared with other agents; load average 4-16
during runs). Test splits only. Cells are **nDCG@10 / hit@10**.

| Method | Natural questions (64, hand-written) | Nave's topic names (334) | Nave's sub-topics (184) | Verse to cross-refs (317) |
|---|---:|---:|---:|---:|
| `/api/search` today (`fts_today`) | 0.024 / 0.05 | 0.299 / 0.74 | 0.012 / 0.03 | 0.000 / 0.00 |
| Keyword, stop-worded OR + BM25 (`fts_or`) | 0.154 / 0.52 | 0.311 / 0.76 | 0.220 / 0.52 | 0.164 / 0.54 |
| potion-base-8M (static, model2vec) | 0.172 / 0.56 | 0.270 / 0.73 | 0.174 / 0.46 | 0.121 / 0.45 |
| all-MiniLM-L6-v2 | 0.275 / 0.73 | 0.236 / 0.69 | 0.208 / 0.54 | 0.131 / 0.47 |
| bge-small-en-v1.5 | 0.257 / 0.69 | 0.214 / 0.70 | 0.174 / 0.48 | 0.131 / 0.49 |
| e5-small-v2 | 0.270 / 0.77 | 0.246 / 0.73 | 0.199 / 0.53 | 0.145 / 0.53 |
| snowflake-arctic-embed-xs | 0.279 / 0.70 | 0.277 / 0.74 | 0.230 / 0.57 | 0.128 / 0.44 |
| mxbai-embed-xsmall-v1 | 0.287 / 0.77 | 0.241 / 0.71 | 0.218 / 0.54 | 0.135 / 0.48 |
| **gte-small (shipped), meaning only** | **0.328 / 0.78** | 0.271 / 0.75 | 0.225 / 0.55 | 0.149 / 0.51 |
| gte-small hybrid (RRF with `fts_or`) | 0.242 / 0.69 | **0.333 / 0.78** | **0.247 / 0.58** | **0.179 / 0.58** |
| gte-small `auto` (API default: hybrid if <= 2 content words) | 0.297 / 0.77 | 0.333 / 0.78 | 0.226 / 0.55 | 0.149 / 0.51 |
| *ceiling: qwen3-embedding 0.6B (Ollama, not shippable)* | *0.413 / 0.92* | *0.246 / 0.69* | *0.231 / 0.54* | *0.198 / 0.64* |

All rows (every model x vec/hybrid/boost/auto) are in `docs/semantic-eval-2026-11.json`;
`python scripts/eval_semantic.py --table docs/semantic-eval-2026-11.json` prints them.

What this says, plainly:

- **On natural questions, meaning search clearly beats keyword search.** Today's search
  finds a listed verse in the top 10 for 3 of 64 questions (it requires every word to
  match). A fair keyword baseline gets 33 of 64; gte-small gets 50 of 64, and nDCG@10 is
  2.1x. With 64 questions the standard error on hit@10 is about 0.05, so the gap to
  keyword search is real; the gaps between the better small models (gte, mxbai, e5,
  MiniLM) on questions alone are not. gte-small is the only one that is also best or near
  best on the Nave's and cross-reference sets, which is why it was chosen.
- **On one-word topics, keyword search is as good or better.** Nave's topic names
  ("Fasting", "Curtains") are keyword search's home ground: meaning-only gte (0.271) is
  below keyword (0.311). Fusing the two (hybrid) is best (0.333). Even the 0.6B qwen3
  ceiling does not beat keyword there.
- **Fusing keywords into long questions hurts** (gte: 0.328 -> 0.242), because question
  words that are not in Scripture's vocabulary ("anxiety", "lonely") pull in verses that
  merely share a word. Hence the API's `auto` mode: hybrid for queries of at most two
  content words, meaning only for longer ones. The cut was fixed before looking at test
  numbers. It wins on topics and loses 0.03 nDCG on questions (some questions are short:
  "what is faith", "love your enemies"). A UI that shows a keyword list beside the meaning
  list should request `mode=meaning`.
- **"More like this" needs both signals.** For verse-to-cross-reference retrieval,
  keyword overlap alone (0.164) beats gte vectors alone (0.149) and the fusion beats both
  (0.179), so `/api/search/similar` fuses them.
- **The quality ceiling is well above what ships.** qwen3-embedding 0.6B reaches 0.413 /
  0.92 on questions. It is 17x the parameters and cannot run per request on a shared-cpu-1x
  machine; see "Closing the gap" below.

### Chosen: gte-small (thenlper/gte-small, int8 ONNX export by Xenova)

| | |
|---|---|
| Model file | 34.7 MB (`onnx/model_quantized.onnx` + tokenizer), MIT, revision `5927d1727bb1` |
| DB bytes added | **16.8 MB** of pages (`semantic_vectors` 16.0 MB: 31,202 x (384 B int8 + 48 B sign bits + scale + ref) + 0.7 MB index). The file grew 12.6 MB (830.6 -> 843.2 MB) because SQLite reused free pages |
| Image added | ~138 MB installed Python wheels (numpy 60, onnxruntime 63, tokenizers 12, protobuf/flatbuffers 3) + 34.7 MB model, uncompressed |
| RAM added | ~141 MB RSS in the web process (onnxruntime + session ~100, numpy ~20, int8 matrix 12, refs ~10), on top of a ~49 MB app. Fly VM is 1 GB |
| Startup | +0.39 s to load model and vectors, in a background thread (does not delay `/api/health`) |
| Query latency, one pinned N100 core | embed 6.8 ms p50 / 9.0 p95; score 31K vectors 7.5 ms; whole `/api/search/meaning` handler 54 ms p50 (the stop-worded FTS query for match flags is most of it); end to end through TestClient 60 ms p50 / 82 ms p95; `/similar` 84 ms p50 |
| Build | 24 min wall, 14 min CPU, single-threaded on the loaded N100 (`threads=1` is the reproducible setting) |

A Fly shared-cpu-1x core is probably slower than an N100 core and is throttled after
bursts; budget 2-3x these latencies (~150 ms). Brute force is fine: scoring is 7.5 ms, so
an ANN index would add complexity and bytes for nothing measurable.

Runner-up / fallback model: **all-MiniLM-L6-v2** (23.7 MB, embed 3.8 ms, 0.275 / 0.73 on
questions). Switch with `SEMANTIC_MODEL=minilm-l6` and rebuild the step. If the model or
vectors are missing at runtime, the endpoint degrades to keyword search (tested).
Static embeddings (potion, no transformer, 0.2 ms) are barely better than keyword search
on questions and are not worth shipping.

### Storage: int8 is free, binary alone is not

gte-small, test splits, nDCG@10 (`--quant`):

| Storage | questions | naves | subtopics | xref | Bytes for 31K verses |
|---|---:|---:|---:|---:|---:|
| float32 | 0.328 | 0.271 | 0.225 | 0.149 | 47.9 MB |
| **int8 + per-vector scale (served)** | **0.331** | 0.268 | 0.221 | 0.149 | 12.1 MB |
| binary (sign bits, Hamming) | 0.160 | 0.157 | 0.143 | 0.090 | 1.5 MB |
| binary top-400, int8 rescoring | 0.325 | 0.255 | 0.222 | 0.145 | 1.5 + 12.1 MB |

The sign bits are kept (1.5 MB) only as an optional prefilter for slow devices.

### Passages and commentary

- **Verse windows** (verse +-1 in the same chapter, mixed with the verse vector): with
  MiniLM, the dev-tuned mix gained +0.02 nDCG on questions and sub-topics and nothing on
  topics or cross-references; with qwen3, +0.04 on questions. Window texts cost 3x the
  embedding time. gte-small ships verse-only (`ALPHA = 1.0` in
  `scripts/build_embeddings.py`; set 0.5 to enable windows, no schema change).
- **Commentary: not embedded.** The cheapest real option, Tyndale's 14,981 short notes (<=
  5 verses each, ~260 chars, ~7 MB of vectors, 14 min to embed), was tested as
  `verse score + gamma x best covering note`. Tuned on dev, gamma came out 0 for
  sub-topics (so no change on questions) and gave +0.012 on Nave's topics. It does not
  earn its bytes. Long-form sources (Henry, Calvin, Gill: 120+ MB of text) would cost far
  more for passage-level vectors. Tyndale is also CC BY-SA; derived vectors would raise a
  share-alike question we do not need to answer.
- Other translations map through the verse reference (one vector per reference); the
  `translation` parameter only changes the text returned.

### Browser / offline (measured, not recommended yet)

`tests/browser/semantic_demo.html` runs the same quantized gte-small in headless Chromium
with transformers.js 3.8.1 (Apache-2.0; bundles onnxruntime-web, MIT) and the exported
vectors (`python scripts/build_embeddings.py --export-browser data/semantic-browser`).

| | Desktop CPU (N100) | 4x CPU throttle (mid phone) |
|---|---:|---:|
| Page ready (vectors + model download from the HF CDN + init) | 3.6 s | 7.3 s |
| Model download + init | 2.8 s | 5.4 s |
| Load 12 MB vectors (local) | 84 ms | 289 ms |
| First query | 252 ms | 701 ms |
| Embed per query (median) | 34 ms | 91 ms |
| Score + sort 31K in plain JS | 42 ms | 140 ms |
| JS heap | 57 MB | 57 MB |

Same top 5 as the server for all six probe queries; the browser query vector has cosine
0.999 with the server's. Renderer RSS rose from 76 MB to 430 MB, but that number sums
every Chromium renderer on this shared machine, so treat it as an upper bound.

What offline would ship: model 34.7 MB + int8 vectors 12.0 MB (9.7 MB gzipped) + scales
0.12 MB + refs 0.31 MB (75 KB gzipped), about **45 MB** cached by the service worker.
Binary vectors alone (1.5 MB) halve quality (table above).

Recommendation: **serve from the server now** (ONNX Runtime). Offer in-browser search
later as an opt-in "download meaning search for offline use (45 MB)", reusing the same
model file and the export above; the JS scoring loop should then use partial selection
instead of a full sort. Fallback in every case: keyword search.

### Where meaning search still fails (real gte-small results)

17 of 64 questions have none of my listed verses in the top 5. Some of those are good
answers my list lacks; others are real failures. Top results, verbatim refs:

- *"what does the Bible say about anxiety"*: Exodus 20:20, **Isaiah 35:4** ("Say to those
  with anxious hearts: Be strong, do not fear", a good answer I did not list), Jeremiah
  30:5, Proverbs 19:23, Jeremiah 20:4. "Anxiety" collapses into fear and terror; the
  classic answers (Philippians 4:6, Matthew 6:34, 1 Peter 5:7) are missing.
- *"God's promises when afraid"*: Exodus 20:20, Psalm 147:11 ("pleased with those who
  fear Him"), Psalm 56:11, Matthew 28:10, Psalm 128:4. "Fear of the LORD" and "be afraid"
  look alike to the model.
- *"be careful what you say"*: Lamentations 3:57, Ecclesiastes 7:21, Deuteronomy 1:29,
  Jeremiah 22:21, Genesis 31:29. It matches the act of saying, not guarding the tongue
  (James 3, Proverbs 18:21).
- *"how can I be saved"*: Luke 18:26 ("Who then can be saved?"), John 5:34, Isaiah 64:5.
  It finds verses that ask the question, not ones that answer it (Romans 10:9, Acts 16:31).
- *"helping the poor and needy"*: Proverbs 31:20 (fine), then Psalm 113:7, Psalm 40:17 ("I
  am poor and needy"): verses about the poor rather than commands to help them.
- *"what does God want from me"*: John 11:22, **Song of Solomon 7:10** ("his desire is for
  me"), Psalm 63:1. Micah 6:8 is missing.
- *"where does Scripture talk about waiting on God"*: the top 10 are all on topic (Psalm
  130:5, 27:14, Lamentations 3:25-26, Psalm 33:20, Isaiah 30:18, Micah 7:7), but
  **Isaiah 40:31 ranks 26th**. The feature's motivating example is not in the first page.
- Good answers I did not list (so the scores understate): Psalm 25:16 ("I am lonely and
  afflicted") for loneliness, Romans 13:6 for taxes, Matthew 21:22 for answered prayer,
  2 Corinthians 1:20 for "God keeps his promises".

### Closing the gap (needs GPU time; not run)

The qwen3 ceiling shows ~+0.09 nDCG@10 / +0.14 hit@10 on questions is available. A small
fine-tune of gte-small keeps the shipped size and latency:

- Data, no generated text: (Nave's sub-topic label, verse) pairs and (topic name, verse)
  pairs from the **train/dev split only** (~25K pairs after the filters in
  `scripts/eval_semantic.py`), plus (verse, cross-reference) pairs from dev sources
  (~20K with votes >= 10). Hard negatives: qwen3-embedding top-50 verses that are not
  labelled (qwen3 as teacher, run on crucible).
- Training: sentence-transformers `MultipleNegativesRankingLoss` (+ optional
  `MarginMSELoss` against qwen3 scores), batch 128, lr 2e-5, 2 epochs, max length 128,
  from `thenlper/gte-small` @ `17e1f347d17f`; one consumer GPU, under an hour.
- Export: ONNX + dynamic int8 quantization (`optimum-cli export onnx`, then
  `onnxruntime.quantization.quantize_dynamic`), add a `ModelSpec`, rerun this harness. The
  hand-written questions and every test split stay untouched, so the comparison stays
  honest. Watch for over-fitting to Nave's 1890s vocabulary.


## How to regenerate

```bash
# vectors (build step `embeddings`; 24 min single-threaded on a loaded N100; downloads the model once)
python scripts/build_db.py --step embeddings
# evaluation (embeddings cached in data/sources/semantic-eval/)
python scripts/eval_semantic.py --verse-only --out docs/semantic-eval-2026-11.json \
  --models potion-8m,potion-retrieval-32m,minilm-l6,bge-small,gte-small,e5-small-v2,arctic-xs,mxbai-xsmall,qwen3
python scripts/eval_semantic.py --table docs/semantic-eval-2026-11.json
python scripts/eval_semantic.py --models minilm-l6,qwen3        # adds the verse+window mix
python scripts/eval_semantic.py --models gte-small --verse-only --quant --notes  # storage, Tyndale
python scripts/eval_semantic.py --models gte-small --sets questions --verse-only --examples
# server cost on one pinned core
python scripts/bench_semantic.py --models gte-small,minilm-l6,potion-8m --cpu 3
# browser proof
python scripts/build_embeddings.py --export-browser data/semantic-browser
python tests/browser/measure_semantic_demo.py [--throttle 4]
pytest tests/test_semantic.py
```

`qwen3` needs `OLLAMA_URL` (default `http://crucible:11434`) with `qwen3-embedding:0.6b`;
it is a quality ceiling only and never on the request path.

## Evaluation design

All labels come from data already in the DB, plus one small hand-written set.

| Set | Queries | Query | Relevant | Notes |
|---|---:|---|---|---|
| questions | 64 | natural questions ("what does the Bible say about anxiety") | 2-9 verses each, written by me | `tests/fixtures/semantic_questions.json`. Small and written by the agent that built the feature, not by users or a pastor. Good answers I did not list count as misses (examples below), so absolute scores understate quality. Never used for tuning |
| naves | 661 (334 test) | a Nave's topic name ("Fasting", "Prosperity") | the topic's verses (median 19) | Concept topics only: the topic word is mostly lowercase in BSB, which drops people and places. Whole-chapter refs and ranges over 10 verses are dropped. One-word queries: this is keyword search's home ground |
| subtopics | 400 (184 test) | "Topic: sub-topic line" ("Death: Promised to saints at the second coming of Christ") | that line's refs (median 4) | Labels with fewer than 3 words or generic ones ("See ...", "Instances of") dropped |
| xref | 600 (317 test) | a verse's BSB text | its OpenBible.info cross-references (TSK-derived, votes >= 10; median 6) | The verse and its +-3 neighbours are excluded from results and labels. Models "more like this" |

Splits are by sha1 of the topic or verse, so all sub-topics of one topic fall on the same
side. Everything tunable (verse/window mix `alpha`, fusion weight `w`, Tyndale weight
`gamma`) is chosen on dev and reported on test. The questions set has no dev side; it uses
the values tuned on the sub-topics dev split.

Metrics: R@10 and R@50 (share of relevant verses retrieved), nDCG@10, MRR (first relevant
within 100) and hit@10 (share of queries with any relevant verse in the top 10; the number
a reader feels).

Methods:

- `fts_today`: the exact query `/api/search` builds today (every word must match, last
  word prefix), over `verses_fts` (all translations, deduplicated to verses).
- `fts_or`: a fairer keyword baseline: stop words and question scaffolding dropped
  ("what does the Bible say about"), crude suffix stripping + prefix match, OR, BM25.
- `vec:<model>:verse`: cosine over one vector per BSB verse. `:mix` adds the verse-with-
  neighbours (+-1 verse, same chapter) vector with weight `1 - alpha`.
- `hybrid:<model>`: reciprocal rank fusion (k=60) of meaning top-100 and `fts_or` top-100.
- `boost:<model>`: meaning top-100 re-ranked by RRF with only those keyword hits that are
  already in the meaning top-100 (keyword-only verses never enter). Helped MiniLM, not
  gte-small; not used by the API.
- `auto:<model>`: `hybrid` when the query has at most two content words, else meaning only.
  The cut was fixed before test results were seen. This is the API default.
- `vec+notes:<model>`: verse score + `gamma` x best covering Tyndale Study Note score.


## API

Spec for the frontend agent. Router: `backend/routers/semantic.py`.

### `GET /api/search/meaning`

| Param | Default | Values |
|---|---|---|
| `q` | required | 2-200 chars |
| `scope` | `all` | `all`, `bible` (same), `ot`, `nt`, `book:<Book>` (canonical name, e.g. `book:Psalms`). `commentary` is not supported: keep `/api/search` for commentary |
| `mode` | `auto` | `auto`: `hybrid` when the query has <= 2 content words, else `meaning`. `hybrid`: RRF of meaning and keyword lists (keyword-only verses can appear). `meaning`: vectors only. The response's `mode` says which ran |
| `translation` | `BSB` | any translation id; text falls back to BSB where that translation lacks the verse. Ranking always uses BSB vectors (one vector per verse reference) |
| `limit` | 30 | 1-100 |

Rate limit 30/min per IP (same as `/api/search`). Responses are cacheable (the existing
middleware gives `/api/search*` a 24 h `Cache-Control`).

Response (same core shape as `/api/search`, so `result-snippet` rendering can be reused):

```json
{
  "query": "where does Scripture talk about waiting on God",
  "scope": "all", "translation": "BSB",
  "mode": "meaning",            // hybrid | meaning | keyword | reference | strongs
  "fallback": false,            // true => meaning search unavailable, results are keyword
  "fallback_reason": "...",     // only when fallback
  "model": "gte-small",
  "took_ms": 23.4,
  "results": [
    {"type": "verse", "book": "Isaiah", "chapter": 40, "verse": 31,
     "snippet": "But those who <mark>wait</mark> upon the LORD will renew ...",
     "score": 0.61,             // cosine similarity, -1..1; comparable within one query only
     "match": "both",           // meaning | keyword | both
     "meaning_rank": 3, "keyword_rank": 12}
  ]
}
```

- `snippet` is HTML-escaped verse text; `<mark>` wraps query words only when the verse also
  matched by keyword (`match` is `keyword` or `both`). Safe for `x-html`, like today.
- `mode: "reference"` (query parses as a reference, e.g. "john 3:16", "Psalms") returns
  `"reference": "John 3:16"` and no results: open the passage, as today.
- `mode: "strongs"` (G26, H430): call `/api/search` as today.
- `mode: "keyword", fallback: true`: model or vectors missing or broken. Same shape;
  `score` is then an RRF value, not a cosine. Show the results without a "by meaning" label.

### `GET /api/search/similar/{reference}`

"More like this verse". `reference` must be one verse (`Isaiah 40:31`); chapters and ranges
give 400. Params: `scope`, `translation`, `limit` (default 20, max 50). Verses within +-3 of
the source in the same chapter are excluded (the reader already sees them). Response:
`{"reference", "scope", "translation", "fallback", "model", "results": [...]}` with the same
result objects (`match: "meaning"`, no `<mark>`). On fallback `results` is empty.

### `GET /api/semantic/status`

`{"available": true, "loaded": true, "error": null, "model": "gte-small"}`. Not cached, so the
UI can hide meaning controls when `available` is false.

### Suggested presentation

- Keep the live, debounced keyword search exactly as it is (it is cheap and good at exact
  words and names). Do not call the meaning endpoint on every keystroke: call it on Enter,
  or once typing pauses for ~600 ms and the query has 3+ words, or from a "Search by
  meaning" button.
- Show the two lists separately, keyword first when the query is one or two words, meaning
  first when it reads like a question (3+ words, or starts with what/how/why/where/verses).
  When the keyword list is shown beside it, call the meaning endpoint with `mode=meaning`
  (fusing keywords into questions hurt in the evaluation; the keyword list already covers
  exact words). A single combined list should use the default `mode=auto`.
  Label the meaning list plainly ("Verses about this idea") and do not show the numeric
  score; a similarity of 0.55 means nothing to a reader. `match: "both"` can get a small
  "contains your words" hint.
- Never present meaning results as an answer. No summary, no "the Bible says". They are
  verses to read in context; each result should open the passage with the verse
  highlighted, as keyword results do.
- Scope chips (All / OT / NT / This book) map to `scope`; reuse the existing ones.
- Study view: a "More like this" action on a verse calls `/api/search/similar/{ref}` and
  lists results next to the TSK cross-references, labelled differently ("Similar wording
  or idea" vs "Cross-references"), since they are a different kind of evidence.
- Offline: until in-browser embedding ships, hide meaning search when offline (or when
  `/api/semantic/status` says unavailable) rather than showing an error.

## Deployment notes (not done here; nothing was deployed)

- `requirements.txt` gains numpy, onnxruntime, tokenizers (pinned). The Dockerfile copies
  `data/models/`; `.dockerignore` keeps only `gte-small@5927d1727bb1/`. If the model
  directory is empty the image still builds and the API falls back to keyword search.
- The DB grows 12.6 MB (843 MB). **Existing risk, made slightly worse:**
  `scripts/entrypoint.sh` copies the image DB to `bible.db.tmp` on the volume while the old
  DB is still there, so a DB-changing deploy needs about 2x the DB size free on the 1 GB
  volume. At 830 MB that was already impossible; check how prod deploys have been
  succeeding (or whether the volume was grown) before shipping any DB change.
- `/api/search*` responses get a 24 h `Cache-Control` from the existing middleware,
  including a keyword fallback served while the model was missing.
- Rebuild the step whenever the model, `ALPHA`, or the unit texts change (bump its version
  in `scripts/build_db.py`). The API refuses vectors whose `model_sha256` does not match
  the model files on disk.

## Found along the way

- `scripts/import_naves.py` `parse_references` drops same-book continuation refs: `PSA
  37:5; 55:22` yields only Psalm 37:5, so `naves_topic_refs` silently misses many verses
  (here Psalm 55:22, "Cast your burden upon the LORD", under CARE, REMEDY FOR). The
  evaluation uses its own parser (`parse_naves_refs`). Not fixed here (not this branch's
  file).
