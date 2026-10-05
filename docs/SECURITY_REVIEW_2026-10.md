# Security Review (2026-10-05)

Scope: the FastAPI backend, the Alpine PWA, the Supabase RLS migrations and CI workflows. Behaviour was confirmed with read-only requests against bible-mvp-dev (never prod).
Verdict: **no critical findings.** Checked and found clean: SQL injection (all queries are parameterised), path traversal, open redirects, and secrets in git history (only the public Supabase anon key appears).

The Status column records what was done on branch `ui/p0-fixes`. **Applied** means changed in code. **Written, not applied** means the SQL is in `supabase/migrations/005_security_hardening.sql` and still has to be run on the Supabase projects. **Open** means deferred.

| # | Sev | Finding | Status |
|---|---|---|---|
| H1 | High | Third-party scripts (supabase-js `@2`, Alpine `3.x.x`) come from CDNs with no SRI. The CSP allows all of unpkg and jsdelivr plus `*.supabase.co`, and has no `base-uri`, `object-src` or `form-action`. | **Applied.** Both libraries are vendored in `/static/vendor` with pinned versions; the supabase-js copy is byte-identical to the CDN's. CDN hosts are removed from `script-src`. `connect-src` is limited to this environment's Supabase host. Added `object-src 'none'`, `base-uri 'self'` and `form-action 'self'`. `'unsafe-eval'` stays, because Alpine needs it. |
| M1 | Med | Shell injection through `${{ inputs.sha }}` in `promote.yml`, which runs with the prod deploy token. | **Applied.** The input now passes through env and must match `^[0-9a-f]{40}$`. The image ref also goes through env. |
| M2 | Med | `find-path` with an unreachable custom seed walked the whole graph: 2.4 s of CPU and an 800 KB response. There was no rate limit, the seed list had no cap, and the queue used `list.pop(0)`. | **Applied.** BFS stops at 2000 nodes and uses a `deque`. Seed lists are capped at 30. Rate limits: 20/min on christological and path-to-christ, 30/min on crossref-map. |
| M3 | Med | FTS5 injection: balanced quotes passed operators straight into the query. `"x" ) OR (book : john` escaped the column filter, and `"a" OR "the" OR …` took 3.8 s. | **Applied.** Queries are rebuilt from quoted terms only, with a maximum of 8 terms. Prefix matching applies only to the last word, and only when it has 3+ characters. `q` is capped at 100 characters. |
| M4 | Med | Bug-screenshot storage policies exist only as commented SQL. As written, uploads were not restricted to the user's own folder, and there was no server-side size or MIME limit. | **Written, not applied:** migration 005. |
| L | Low | `bug_reports` INSERT let users set `status` and `admin_notes`, spoof `user_email`, and post unbounded text. `user_notes.content` was also unbounded. | **Written, not applied:** migration 005. |
| L | Low | `note_tags` INSERT didn't check that the tag belongs to the user. | **Written, not applied:** migration 005. |
| L | Low | `reading_plan_progress` has no UPDATE policy, but the client upserts into it. This is a functional bug. | **Written, not applied:** migration 005. |
| L | Low | Topics `limit=-1` / `per_page=-1` returned everything. | **Applied:** `ge=1`. |
| L | Low | No HSTS or Permissions-Policy header. | **Applied.** |
| L | Low | Redirects downgraded to `http://` because uvicorn didn't trust Fly's forwarded headers. | **Applied:** `--proxy-headers --forwarded-allow-ips='*'`. |
| L | Low | `/docs` and `/openapi.json` are public. | **Applied:** disabled when `APP_ENV=prod`. Dev keeps them. |
| L | Low | CI used `setup-flyctl@master` and had no `permissions:` block. | **Applied:** pinned to a commit SHA, `permissions: contents: read`. |
| L | Low | `x-html` renders server data without sanitising it: topic text, parallel diff, verse text, search snippets. It's exploitable only if the DB or an IndexedDB cache is poisoned. Notes are already escaped. | **Open.** Sanitise when the UI overhaul touches these templates. |
| L | Low | Python dependencies other than fastapi, uvicorn and slowapi float, with no lockfile or audit. | **Open.** Add constraints and run `pip-audit` in CI. |
| L | Low | The service worker caches every same-origin 200 response in an unbounded static cache. Only the user's own browser can be affected. | **Open** (also covered by the bug review). |
| L | Low | `/api/health` runs 6 `COUNT(*)` queries per call, with no rate limit. | **Open.** It's cheap at current scale. |
| L | Low | The in-memory rate limiter works per machine, and `Fly-Client-IP` would be the better key. Spoofing the leftmost `X-Forwarded-For` value was tested and **cannot** bypass it. | **Open.** It's fine on a single machine. |

Couldn't verify from the repo: Supabase Auth settings (email confirmation, password policy, signup rate limits) and the grants on the live tables. Check these in the dashboard.
