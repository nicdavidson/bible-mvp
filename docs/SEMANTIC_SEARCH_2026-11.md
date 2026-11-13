# Meaning search (2026-11)

Branch `v2/search`. Adds search by meaning over Bible verses, so "where does Scripture talk
about waiting on God" finds Isaiah 40:31 without the reader typing its words, plus "more
like this verse". It finds and ranks existing verses. It never writes text.

## Results in brief

Measured 2026-11-13 on `bridge` (N100, 4 cores, shared with other agents; load average 4-16
during runs). Test splits only. Cells are **nDCG@10 / hit@10**.

Questions are scored twice:
- **listed**: the 351 verses I wrote down beforehand;
- **pooled**: those plus 631 verses judged relevant out of every method's top 10 (see
  "Pooled judging").

| Method | Questions, listed (64) | Questions, pooled (64) | Nave's topic names (334) | Nave's sub-topics (184) | Verse to cross-refs (317) |
|---|---:|---:|---:|---:|---:|
| `/api/search` today (`fts_today`) | 0.024 / 0.05 | 0.028 / 0.06 | 0.299 / 0.74 | 0.012 / 0.03 | 0.000 / 0.00 |
| Keyword, stop-worded OR + BM25 (`fts_or`) | 0.154 / 0.52 | 0.258 / 0.77 | 0.311 / 0.76 | 0.220 / 0.52 | 0.164 / 0.54 |
| potion-base-8M (static, model2vec) | 0.172 / 0.56 | 0.295 / 0.86 | 0.270 / 0.73 | 0.174 / 0.46 | 0.121 / 0.45 |
| all-MiniLM-L6-v2 | 0.275 / 0.73 | 0.391 / 0.97 | 0.236 / 0.69 | 0.208 / 0.54 | 0.131 / 0.47 |
| bge-small-en-v1.5 | 0.257 / 0.69 | 0.389 / 0.98 | 0.214 / 0.70 | 0.174 / 0.48 | 0.131 / 0.49 |
| e5-small-v2 | 0.270 / 0.77 | 0.389 / 0.98 | 0.246 / 0.73 | 0.199 / 0.53 | 0.145 / 0.53 |
| snowflake-arctic-embed-xs | 0.279 / 0.70 | 0.390 / 0.98 | 0.277 / 0.74 | 0.230 / 0.57 | 0.128 / 0.44 |
| mxbai-embed-xsmall-v1 | 0.287 / 0.77 | 0.416 / 0.97 | 0.241 / 0.71 | 0.218 / 0.54 | 0.135 / 0.48 |
| **gte-small (shipped), meaning only** | **0.328 / 0.78** | **0.465 / 0.98** | 0.271 / 0.75 | 0.225 / 0.55 | 0.149 / 0.51 |
| gte-small hybrid (RRF with `fts_or`) | 0.242 / 0.69 | 0.388 / 0.89 | **0.333 / 0.78** | **0.247 / 0.58** | **0.179 / 0.58** |
| gte-small `auto` (API default: hybrid if <= 2 content words) | 0.297 / 0.77 | 0.436 / 0.94 | 0.333 / 0.78 | 0.226 / 0.55 | 0.149 / 0.51 |
| gte-small control (same model through our export) | 0.332 / 0.78 | 0.469 / 0.97 | 0.271 / 0.75 | 0.219 / 0.53 | 0.148 / 0.51 |
| **gte-small fine-tuned (round two), meaning only** | 0.342 / 0.80 | 0.487 / 1.00 | 0.279 / 0.73 | 0.247 / 0.58 | 0.208 / 0.66 |
| gte-small fine-tuned, `auto` | 0.326 / 0.80 | 0.469 / 0.98 | 0.320 / 0.78 | 0.248 / 0.58 | 0.208 / 0.66 |
| *ceiling: qwen3-embedding 0.6B (Ollama, not shippable)* | *0.413 / 0.92* | *0.611 / 1.00* | *0.246 / 0.69* | *0.231 / 0.54* | *0.198 / 0.64* |

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
  machine. The round-two fine-tune of gte-small did not close the gap on questions; see
  "Fine-tune" below.
- **Pooled labels raise every method and keep the order.** gte-small stays the best small
  model (0.465), and meaning beats keyword by +0.207 nDCG@10 (95% bootstrap interval
  +0.148 to +0.265). With pooled labels, hit@10 saturates near 1.0 for every embedding
  model, so nDCG@10 is the number to read there.

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

### Fine-tune (round two): run, and not shipped

**Verdict: keep stock gte-small.**
- **Questions (the judge):** the fine-tune does not improve them by more than noise, on
  either label set or in either mode.
- **Nave's topics:** no clear change.
- **Cross-references:** clearly better (+0.060 nDCG@10, +0.15 hit@10). Using the fine-tuned
  vectors only for `/api/search/similar` would cost a second 16 MB vector table and ~40 MB
  more RAM; that is a separate decision.

Paired bootstrap, fine-tuned minus control (the same base through the same export), 10,000
resamples, 95% intervals:

| Set | nDCG@10 | hit@10 |
|---|---|---|
| Questions, listed, meaning only | +0.010 [-0.032, +0.053] | +0.016 [-0.094, +0.125] |
| Questions, pooled, meaning only | +0.018 [-0.033, +0.068] | +0.031 [+0.000, +0.078] |
| Questions, listed, `auto` (vs stock) | +0.029 [-0.004, +0.060] | +0.031 [-0.078, +0.141] |
| Nave's topics, meaning only | +0.007 [-0.010, +0.025] | -0.021 [-0.063, +0.021] |
| Nave's topics, `auto` | -0.009 [-0.025, +0.007] | -0.009 [-0.042, +0.027] |
| Nave's sub-topics | +0.028 [+0.004, +0.053] | +0.049 [+0.000, +0.098] |
| Cross-references | **+0.060 [+0.044, +0.076]** | **+0.151 [+0.101, +0.202]** |

Same failure queries, top 5 before (stock) and after (fine-tuned). `*` = a listed answer,
`+` = judged relevant in pooling:

| Query | Stock gte-small | Fine-tuned |
|---|---|---|
| what does the Bible say about anxiety | Exodus 20:20; Isaiah 35:4+; Jeremiah 30:5; Proverbs 19:23; Jeremiah 20:4 | **1 Peter 5:7\*; Isaiah 35:4+; Psalms 94:19\*; Proverbs 12:25+**; Job 15:4 |
| God's promises when afraid | Exodus 20:20; Psalms 147:11; Psalms 56:11+; Matthew 28:10; Psalms 128:4 | Haggai 2:5+; Deuteronomy 1:29; Psalms 56:3\*; Romans 4:21; 2 Chronicles 26:5 |
| be careful what you say | Lamentations 3:57; Ecclesiastes 7:21; Jeremiah 22:21; Deuteronomy 1:29; Genesis 31:29 | Mark 13:11; Genesis 31:29; Ezekiel 3:6; Proverbs 4:24+; Job 13:7 |
| how can I be saved | Luke 18:26; Isaiah 64:5; John 5:34; Psalms 55:16; Isaiah 45:22+ | Luke 18:26; Mark 10:26; Acts 15:11+; Matthew 19:25; Hebrews 7:25+ |
| helping the poor and needy | Proverbs 31:20+; Psalms 113:7; Proverbs 31:9+; Psalms 40:17; Psalms 70:5 | Psalms 107:41; Psalms 113:7; Proverbs 31:20+; Psalms 72:12; Psalms 70:5 |
| what does God want from me | Song of Solomon 7:10; John 11:22; Job 6:8; Psalms 63:1; Philippians 4:19 | Mark 5:7; Job 6:8; Song of Solomon 7:10; Mark 10:36; John 11:22 |
| waiting on God: rank of Isaiah 40:31 | 26 | 39 |

- **Anxiety improved sharply:** the classic answers appear.
- **"Promises when afraid" and "be careful what you say":** a little better.
- **"How can I be saved":** the same failure in a new form; it now returns three verses that
  ask the question (Luke 18:26, Mark 10:26, Matthew 19:25).
- **"Helping the poor" and "what does God want from me":** unchanged failures.
- **Isaiah 40:31:** falls further.
The Nave's-style training data teaches the model what Scripture discusses together (hence
the cross-reference gain), not how modern questions map to answers.

How it was run (all pinned; `scripts/finetune_job.sh`):

- **Data**: `scripts/finetune_data.py`, sha256 `cf80cdacecb8...`, reproduced byte-for-byte by
  a second run.
  - 16,146 (query, positive, hard negative) triplets: 8,006 from Nave's topic names and
    sub-topic lines, 8,140 from cross-references.
  - Only the **dev** side of the evaluation split is used. Dev is split again, 80% train
    and 20% select (model selection only, never trained on).
  - Test queries, test cross-reference sources and all 64 questions are excluded by verse
    index **and by text**: 423 BSB verse texts occur more than once, and a first run that
    excluded by index only let 6 identical strings through.
  - Hard negatives are qwen3-embedding ranks 30-100 that are not positives or within +-2
    verses of one. No generated text anywhere.
  - `tests/test_finetune_data.py` checks all of this against the actual files.
- **Training**: `scripts/finetune_semantic.py`.
  - Base `thenlper/gte-small` @ `17e1f347d17f`; MultipleNegativesRankingLoss, scale 20, no
    duplicate anchors per batch; batch 64, 3 epochs, warmup 10%, weight decay 0.01, max
    length 128, fp32; seed 1234 with deterministic cuDNN.
  - Learning rate swept over {1e-5, 2e-5, 5e-5} (pre-registered). Select nDCG@10 every 100
    steps; best was 5e-5 at step 500 (select 0.257, base 0.216).
  - torch 2.5.1+cu121, sentence-transformers 3.3.1, transformers 4.46.3, onnxruntime 1.20.1.
  - GTX 1080 via `gpu-job` (tenant `personal`, `--gpu 1080 --mem 7 --max-hours 2`); 11 min
    of training, 38 min for the whole job.
- **Export**: `torch.onnx.export` (opset 14) then dynamic int8 (per-channel QInt8). The
  untouched base through the same path is the control; it matches the published Xenova
  int8 export within 0.005 nDCG.
  - Fine-tuned ONNX sha256 `0ada61452b2a...`, control `35d3ffdd8dd7...` (identical in both
    jobs).
- **Where the weights would live** (designed, nothing uploaded):
  - `scripts/release_model.py` publishes to the release bucket under the immutable prefix
    `models/<key>/<sha12>/`: model, tokenizer, spec, run.json and the training-data tarball.
  - A `ModelSpec(..., source="bucket:models/<key>/<sha12>", sha256=pins)` makes
    `fetch_model()` and CI's `scripts/fetch_model.py` fetch it deterministically, verified
    against the pins.
- **Reproducibility caveat:** int8 ONNX output differs slightly by CPU instruction set. The
  control scored 0.323 with query vectors computed on crucible and 0.332 on bridge, with the
  same files. Vectors and queries are bit-reproducible on one CPU type, not across
  machines. Quality is unaffected (browser vs server cosine 0.999), but compare
  `vectors_sha256` only between builds on the same hardware.

### Pooled judging

- **Pool:** for each of the 64 questions, the union of the top 10 from every method in the
  table: both keyword baselines and vec/hybrid/boost/auto for all twelve embedding models,
  including both fine-tunes and qwen3. Verses already listed were removed, leaving 3,936
  candidates (~62 per question).
- **Judging:**
  - Candidates were judged against `tests/fixtures/pooled_judging_rubric.md`, blind to which
    method found them, in canonical order.
  - 3,861 were split across four sub-agents (the same model as me, so this is consistency,
    not independence). I judged the 75 that the final runs added.
  - I audited 48 random sub-agent decisions blind (24 yes, 24 no) and agreed with all 48.
- **Result:** 631 verses (16%) judged relevant, stored as `pooled_refs` beside the original
  `refs`.
- **Caveat:** a verse no method put in its top 10 is still unjudged and counts as a miss.
  Pooling over a dozen models makes that unlikely, not impossible.

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
# round two: fine-tune data (needs Ollama qwen3 for negatives), GPU job, comparisons
python scripts/finetune_data.py                                   # -> data/finetune/cf80cdacecb8
ssh crucible gpu-job submit --tenant personal --gpu 1080 --mem 7 --max-hours 2 \
    --name bible-gte-ft --cwd "$PWD" -- scripts/finetune_job.sh cf80cdacecb8
python scripts/eval_semantic.py --models gte-small,gte-small-ctrl,gte-small-bible --verse-only \
    --pool pool.json --out eval.json                               # pool = unjudged candidates
python scripts/eval_semantic.py --compare docs/semantic-eval-2026-11.json \
    vec:gte-small-ctrl:verse vec:gte-small-bible:verse            # paired bootstrap
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

Rate limit 30/min per IP (same as `/api/search`). Normal responses carry
`Cache-Control: public, max-age=3600` and a weak `ETag` tied to the DB release and image, so a
repeat request with `If-None-Match` gets a 304. A keyword fallback carries `no-store`, so it
is never cached in place of real results.

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

### What the frontend does (`v2/searchui`)

Mostly as suggested above; details and the reasons in `docs/UI_OVERHAUL.md` ("Status
after `v2/searchui`"). Differences: meaning results also load at once when no verse has
the typed words; when none of the words occur in Scripture at all (no result with
`match` other than `meaning`, and no keyword hits) the list is withheld behind "Show the
closest verses anyway", because the nearest verses to a typo are noise; "more like this"
is a section at the end of the Cross-references pane, loaded on request, not a separate
list beside them.

## Deployment notes (not done here; nothing was deployed)

- `requirements.txt` gains numpy, onnxruntime and tokenizers (pinned).
- **Model in the image:** CI now runs `scripts/fetch_model.py` after `fetch_db.py`. It
  reads which model the DB's vectors were built with (`semantic_meta`) and downloads exactly
  those files, checked against per-file sha256 pins and the DB's fingerprint. The
  Dockerfile copies `data/models/`, and `.dockerignore` keeps only the shipped model.
  Before round two, CI never populated `data/models/`, so a CI-built image would always
  have served keyword fallbacks.
- **Volume:** the DB grows 12.6 MB (843 MB). The old entrypoint could not install a DB
  this size on a 1 GB volume; see `docs/DB_UPDATE_PATH_2026-11.md` for the fix
  (`scripts/sync_db.py`) and the owner's commands.
- **Caching:** `/api/search*` responses get `max-age=3600` and an ETag tied to the loaded DB
  release and image (`backend/release.py`); `If-None-Match` returns 304. Keyword fallbacks
  from the meaning endpoints are `no-store`. Other immutable paths keep 24 h.
- Rebuild the `embeddings` step whenever the model, `ALPHA` or the unit texts change (bump
  its version in `scripts/build_db.py`). The API refuses vectors whose `model_sha256` does
  not match the model files on disk.

## Found along the way (fixed in round two)

- `scripts/import_naves.py` dropped same-book continuation refs (`PSA 37:5; 55:22` kept only
  37:5). Fixed: 49,399 -> 75,878 rows in `naves_topic_refs`, none lost (see the round-two
  report). `/api/topics/for-verse` also matched any single-verse ref at or before the
  requested verse; fixed in `backend/routers/topics.py`.
