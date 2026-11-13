#!/usr/bin/env python3
"""Measure tests/browser/semantic_demo.html in headless Chromium (not part of pytest).

Reports model download+init time, vector load time, query latency, renderer memory, and
the cosine between the browser's query vector and the server encoder's (parity check).

    python scripts/build_embeddings.py --export-browser data/semantic-browser
    python tests/browser/measure_semantic_demo.py [--throttle 4]

--throttle N slows the CPU N times via DevTools (4 ~ a mid-range phone).
Needs: playwright with Chromium, numpy, the server-side model in data/models/.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

QUERIES = ["where does Scripture talk about waiting on God", "what does the Bible say about anxiety",
           "verses about forgiving someone who keeps hurting you", "God's promises when afraid",
           "how should a husband treat his wife", "comfort for someone who is grieving a death"]


def renderer_rss_mb(browser_pid: int | None) -> float:
    """Sum RSS of Chromium renderer processes (children of the browser)."""
    total = 0
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            cmd = (p / "cmdline").read_bytes().decode(errors="ignore")
            if "--type=renderer" not in cmd:
                continue
            for line in (p / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1])
        except OSError:
            continue
    return round(total / 1024, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--throttle", type=float, default=1.0)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--enable-precise-memory-info"])
            page = browser.new_page()
            cdp = page.context.new_cdp_session(page)
            if args.throttle != 1:
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": args.throttle})
            rss0 = renderer_rss_mb(None)
            t0 = time.time()
            page.goto(f"http://127.0.0.1:{args.port}/tests/browser/semantic_demo.html")
            page.wait_for_function("window.semanticProbe && window.semanticProbe.ready",
                                   timeout=300_000)
            ready_s = time.time() - t0
            stats = page.evaluate("window.semanticProbe.stats")
            lat = []
            tops = {}
            for q in QUERIES:
                r = page.evaluate("async q => { const r = await window.semanticProbe.run(q);"
                                  " return {e: r.embed_ms, s: r.score_ms, top: r.hits.map(h => h.ref)} }", q)
                lat.append((r["e"], r["s"]))
                tops[q] = r["top"][:5]
            bvec = page.evaluate("t => window.semanticProbe.embed(t)", QUERIES[0])
            rss1 = renderer_rss_mb(None)
            browser.close()
    finally:
        srv.shutdown()

    import numpy as np

    from backend.semantic import CANDIDATES, SHIPPED_MODEL, Encoder, model_dir
    spec = CANDIDATES[SHIPPED_MODEL]
    svec = Encoder(spec, model_dir(spec)).embed([QUERIES[0]], is_query=True)[0]
    cos = float(np.dot(svec, np.array(bvec, dtype=np.float32)))
    report = {"cpu_throttle": args.throttle, "page_ready_s": round(ready_s, 1), **stats,
              "embed_ms_median": round(float(np.median([e for e, _ in lat])), 1),
              "score_ms_median": round(float(np.median([s for _, s in lat])), 1),
              "renderer_rss_mb_before": rss0, "renderer_rss_mb_after": rss1,
              "browser_vs_server_cosine": round(cos, 5), "top5": tops}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
