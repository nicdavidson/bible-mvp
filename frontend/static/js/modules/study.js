// bibleApp feature module: study — the verse/range study view with commentary.
// Merged via Object.assign in app.js. Markup: <dialog class="study-view"> in index.html.
//
// Data: GET /api/passage/{ref}/study (selection text + every source's availability)
// and GET /api/passage/{Book Ch}/commentary?source=slug (one source, whole chapter,
// cached in memory + IndexedDB so moving the selection inside a chapter is instant
// and the view works offline for chapters that were downloaded or studied).
window.BibleModules = window.BibleModules || {};
(() => {
    const PREFS_KEY = 'studySourcePrefs';   // { order: [slug], hidden: [slug], last: slug }
    const META_KEY = 'studySourceMeta';     // last known source metadata, for offline
    const KIND_LABEL = {
        verse: 'Comments verse by verse',
        passage: 'Comments on a passage at a time',
        chapter: 'Comments on the whole chapter',
        notes: 'Short notes on selected verses',
    };
    // First-time order, set by the site owner (same as scripts/commentary_registry.py
    // DEFAULT_ORDER). Sources not listed follow in commentary_sources.sort_order. The
    // reader's own order (Your sources) replaces this. The view opens on the first source
    // in the order that has something on the selection (openStudy), so a sparse source
    // first (Scofield) never opens as an empty pane.
    const DEFAULT_ORDER = [
        'scofield-notes-1917', 'john-gill', 'jamieson-fausset-brown', 'tyndale-study-notes',
        'gaebelein-annotated-bible', 'ironside-expositions', 'newell-verse-by-verse', 'darby-synopsis',
        'brooks-summarized-bible', 'mackintosh-notes-on-the-pentateuch', 'larkin-on-revelation',
        'treasury-of-david',
    ];
    const CHIP_MARGIN = 14;                 // the active chip never sits closer than this to an edge
    const chapterCache = new Map();         // "Book|ch|slug" -> entries (whole chapter)
    let paneObserver = null;

    const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isWide = () => window.matchMedia('(min-width: 960px)').matches;
    const slugify = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'source';
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const readJSON = (key, fallback) => {
        try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
    };
    const writeJSON = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* quota/private */ } };

    // ---- commentary HTML: allowlist sanitizer (sources are imported from many places) ----
    const ALLOWED = new Set(['B', 'BR', 'EM', 'I', 'STRONG', 'SPAN', 'SUP', 'SUB', 'SMALL', 'A',
        'BLOCKQUOTE', 'UL', 'OL', 'LI', 'CITE', 'Q', 'P']);
    function sanitize(html) {
        const tpl = document.createElement('template');
        tpl.innerHTML = html;  // template content is inert: no scripts run, no images load
        const walk = (node) => {
            for (const el of [...node.children]) {
                walk(el);
                const ref = el.tagName === 'A' ? el.getAttribute('data-ref') : null;
                if (!ALLOWED.has(el.tagName) || (el.tagName === 'A' && !ref)) {
                    el.replaceWith(...el.childNodes);
                    continue;
                }
                for (const a of [...el.attributes]) el.removeAttribute(a.name);
                if (ref) {
                    el.setAttribute('href', '#');
                    el.setAttribute('class', 'commentary-ref');
                    el.setAttribute('data-ref', ref);
                }
            }
        };
        walk(tpl.content);
        return tpl.innerHTML;
    }

    // Puritan-style outline markers: I. / 1. / (1.) / [1.] / a. / (a.) / [a.]
    const OUTLINE = [
        [/^([IVXL]+\.)\s+/, 1], [/^(\d+\.)\s+/, 2], [/^(\(\d+\.?\))\s*/, 3], [/^(\[\d+\.?\])\s*/, 4],
        [/^([a-z]\.)\s+/, 5], [/^(\([a-z]\.?\))\s*/, 6], [/^(\[[a-z]\.?\])\s*/, 7],
    ];

    // Same rules as backend effective_ranges(): passage rows stored with only a
    // start verse run until the next row of that source (offline/IDB path).
    function effectiveRanges(rows, kind, last) {
        const starts = rows.map(r => r.reference_start || 1);
        return rows.map((r, i) => {
            if (r.range_start != null && r.range_end != null) return [r.range_start, r.range_end];
            const start = starts[i];
            const end = r.reference_end;
            if (kind === 'chapter') return [1, Math.max(last, start)];
            if (end != null && end > start) return [start, end];
            if (kind === 'passage') {
                const next = starts.slice(i + 1).find(s => s > start);
                return [start, next ? next - 1 : Math.max(last, start)];
            }
            return [start, end || start];
        });
    }

    // ---------- entry text analysis (pure; exposed as window.BibleStudyText for tests) ----------
    // A verse marker at the start of a paragraph: "Verse 16." (Barnes, Clarke, Spurgeon),
    // "Ver. 16." (Catena), "Verses 16-18". Calvin's bare "16." is handled per entry below.
    const MARKER_RE = /^(?:Verses?|Ver\.|Vv?\.)\s*(\d+)(?:\s*[-–]\s*(\d+))?\.?(?=\s|$)\s*/i;
    const NUMERIC_RE = /^(\d+)\.?\s+(?=["'(\u201c]?[A-Z])/;   // "16. For God", "6 Therefore"
    const SPEAKER_RE = /^([A-Z][A-Za-z]+(?: (?:of )?[A-Z][a-z]+)?):\s/;   // Catena: "Augustine: ..."
    const plain = (html) => html.replace(/<[^>]*>/g, '');
    const overlaps = (a, b, vs, ve) => a <= ve && b >= vs;

    function parseRefParts(ref) {
        const m = String(ref || '').trim().match(/^(.+?)\s+(\d+)(?::(\d+)(?:\s*[-–]\s*(\d+))?)?$/);
        if (!m) return null;
        const vs = m[3] ? parseInt(m[3]) : null;
        return { book: m[1], chapter: parseInt(m[2]), vs, ve: m[4] ? parseInt(m[4]) : vs };
    }

    // Split an entry into paragraphs and work out which verse each one is about.
    // ctx: { book, chapter, vs, ve } (the selection). Returns
    // { paras: [{ html, text, verses, marker, outline, speaker }], mode, wide }
    function analyzeEntry(entry, ctx) {
        const rs = entry.range_start ?? entry.reference_start;
        const re = entry.range_end ?? entry.reference_end ?? rs;
        const wide = (re - rs) > (ctx.ve - ctx.vs);
        let raws = String(entry.content || '').split(/\n\s*\n|\n/).map(p => p.trim()).filter(Boolean);

        // A leading link to the entry's own verses duplicates our heading (Tyndale "3:16 ...")
        if (raws.length) {
            const m = raws[0].match(/^<a\b[^>]*data-ref="([^"]+)"[^>]*>[^<]*<\/a>\s*/);
            const r = m && parseRefParts(m[1]);
            if (r && r.chapter === ctx.chapter && r.vs === rs && (r.ve ?? r.vs) === re) {
                raws[0] = raws[0].slice(m[0].length);
                if (!raws[0]) raws.shift();
            }
        }

        // Calvin numbers his sections "13.", "14.", "16." at paragraph starts. Accept bare
        // numbers as verse markers only when the entry opens with its own first verse and
        // they climb within its range; Henry's outline "1. 2. 1." restarts and is rejected.
        // Calvin's Harmony opens with link-only headers ("Matthew 5:1-12", "Luke 6:20-26") and
        // mixes in the other gospel's numbers; those out-of-range numbers are ignored.
        const linkOnly = (r) => /^<a\b[^>]*>[^<]*<\/a>\.?$/.test(r);
        const firstText = raws.findIndex(r => !linkOnly(r));
        const nums = raws.map(r => (plain(r).match(NUMERIC_RE) || [])[1]).map(n => n && parseInt(n));
        const inRange = nums.filter(n => n && n >= rs && n <= re);
        // (English then Latin repeats a number, so equal neighbours are fine)
        const numericMarkers = firstText >= 0 && nums[firstText] >= rs && nums[firstText] <= re
            && inRange.every((n, i) => i === 0 || n >= inRange[i - 1]);

        let current = null;
        let markerCount = 0;
        const segs = [];
        const paras = [];
        for (const raw of raws) {
            const text = plain(raw);
            let html = raw;
            let marker = null;
            // K&D and Calvin's Harmony head sections with a link to the verse: "Gen 1:3" or
            // "Matthew 5:1. He went up..." (a link into this chapter, opening the paragraph)
            const lm = raw.match(/^<a\b[^>]*data-ref="([^"]+)"[^>]*>[^<]*<\/a>\.?(?:\s+|$)/);
            const lr = lm && parseRefParts(lm[1]);
            const linkMarker = lr && lr.vs && lr.chapter === ctx.chapter && normalizeBookName(lr.book) === ctx.book
                && !(lr.vs === rs && (lr.ve ?? lr.vs) === re && re > rs)   // a header for the whole entry
                ? [lm[0], String(lr.vs), lr.ve && lr.ve !== lr.vs ? String(lr.ve) : undefined] : null;
            const sm = text.match(MARKER_RE);
            const nm = numericMarkers && (text.match(NUMERIC_RE) || [])[1] >= rs
                && (text.match(NUMERIC_RE) || [])[1] <= re ? text.match(NUMERIC_RE) : null;
            const m = sm || nm;
            if (linkMarker) {
                const a = parseInt(linkMarker[1]);
                const b = linkMarker[2] ? parseInt(linkMarker[2]) : a;
                if (a >= rs && a <= re) {
                    marker = [a, Math.max(a, b)];
                    current = [a, Math.max(a, b)];
                    segs.push(current);
                    markerCount++;
                    html = html.slice(linkMarker[0].length);
                }
            } else if (m && !(nm && current && current[0] === parseInt(m[1]))) {
                const a = parseInt(m[1]);
                const b = sm && m[2] ? parseInt(m[2]) : a;
                if (a >= rs && a <= re) {
                    marker = [a, Math.max(a, b)];
                    current = [a, Math.max(a, b)];
                    segs.push(current);
                    markerCount++;
                    if (html.startsWith(m[0].trimEnd())) html = html.slice(m[0].length);
                    else html = html.replace(m[0].trim(), '').trimStart();
                }
            }
            // A paragraph that is only a marker ("Verse 16") heads the paragraphs after it
            if (marker && !plain(html).trim()) continue;
            const speaker = (text.match(SPEAKER_RE) || [])[1] || null;
            const outline = !numericMarkers && /^[IVXL]+\.\s/.test(text) ? text.slice(0, 70) : null;
            paras.push({ html, text: plain(html), verses: current, marker, speaker, outline });
        }

        // A section runs until the next marker: Calvin's "14." also covers an unmarked v15
        segs.forEach((seg, k) => { seg[1] = Math.max(seg[1], (segs[k + 1] ? segs[k + 1][0] : re + 1) - 1); });

        // One marker that ends up spanning the whole entry (Catena's "Ver. 1." above a
        // quotation of verses 1-3) says nothing about which part is which
        if (segs.length === 1 && segs[0][0] <= rs && segs[0][1] >= re) markerCount = 0;

        // Which paragraphs are about the selection
        let mode = 'none';
        if (wide && markerCount) {
            mode = 'markers';
            for (const p of paras) p.focus = !!p.verses && overlaps(p.verses[0], p.verses[1], ctx.vs, ctx.ve);
        } else if (wide) {
            mode = 'mentions';
            for (const p of paras) p.focus = mentionsSelection(p, ctx);
        }
        // Single-verse entries: the opening marker equals our "Verse N" heading
        if (!wide && paras[0]?.marker && paras[0].marker[0] === rs) paras[0].marker = null;
        return { paras, mode, wide, markerCount, rs, re, length: String(entry.content || '').length };
    }

    // data-ref links into this chapter, or "ver. 16", "v. 16", "verse 16", "vv. 16-18" in the text
    // Only narrow mentions count: Henry's chapter outline "(v. 1-21)" is not about v16.
    function mentionsSelection(p, ctx) {
        const maxSpan = Math.max(2, ctx.ve - ctx.vs);
        const hit = (a, b) => b - a <= maxSpan && overlaps(a, b, ctx.vs, ctx.ve);
        // A paragraph that walks through many verses (a chapter outline) isn't "about" one
        const cited = new Set();
        let hits = 0;
        for (const m of p.html.matchAll(/data-ref="([^"]+)"/g)) {
            const r = parseRefParts(m[1]);
            if (!(r && r.chapter === ctx.chapter && r.vs && normalizeBookName(r.book) === ctx.book)) continue;
            cited.add(r.vs);
            if (hit(r.vs, r.ve ?? r.vs)) hits++;
        }
        if (hits) return !(cited.size >= 4 && hits / cited.size < 0.5);
        for (const m of p.text.matchAll(/\b(?:verses?|vers?\.|vv?\.)\s*(\d+)(?:\s*[-–]\s*(\d+))?/gi)) {
            const a = parseInt(m[1]); const b = m[2] ? parseInt(m[2]) : a;
            if (hit(a, b)) return true;
        }
        return false;
    }

    // Jump points inside a long entry: verse markers, else Henry's I./II., else Catena's Fathers
    function entryOutline(a) {
        if (a.length < 6000) return [];
        const byMarker = a.paras.map((p, i) => p.marker && { i, label: `v${p.marker[0]}${p.marker[1] > p.marker[0] ? '–' + p.marker[1] : ''}`, hint: p.text.slice(0, 48) }).filter(Boolean);
        if (byMarker.length >= 2) return byMarker;
        const byOutline = a.paras.map((p, i) => p.outline && { i, label: p.outline.match(/^[IVXL]+\./)[0], hint: p.outline.replace(/^[IVXL]+\.\s*/, '').slice(0, 48) }).filter(Boolean);
        if (byOutline.length >= 2) return byOutline;
        const bySpeaker = a.paras.map((p, i) => p.speaker && { i, label: p.speaker, hint: '' }).filter(Boolean);
        return bySpeaker.length >= 3 ? bySpeaker : [];
    }

    // "John Gill (1697-1771)" under the title "John Gill" -> just the dates
    function whoLine(src) {
        const author = String(src.author || '').trim();
        const m = author.match(/^(.*?)\s*\(([^)]*\d[^)]*)\)\s*$/);
        const name = m ? m[1] : author;
        const life = m ? m[2].replace(/-/g, '–') : null;
        const norm = s => s.toLowerCase().replace(/[^a-z]/g, '');
        const sameAsTitle = name && norm(src.source).startsWith(norm(name));
        return {
            author: sameAsTitle ? null : (author.replace(/(\d)-(\d)/g, '$1–$2') || null),
            life: sameAsTitle ? life : null,
            year: src.year ? `published ${src.year}` : null,
            tradition: src.tradition || null,
        };
    }

    // The reader's saved order merged with the library's default order. Saved slugs no
    // longer in the library are dropped. A source the saved order doesn't know (added in a
    // later release) goes where the default order puts it: straight after the nearest source
    // that comes before it by default, or first if none does.
    function mergeOrder(saved, defaults) {
        const known = new Set(defaults);
        const out = [];
        for (const s of saved || []) if (known.has(s) && !out.includes(s)) out.push(s);
        defaults.forEach((slug, i) => {
            if (out.includes(slug)) return;
            let at = 0;
            for (let j = i - 1; j >= 0; j--) {
                const k = out.indexOf(defaults[j]);
                if (k >= 0) { at = k + 1; break; }
            }
            out.splice(at, 0, slug);
        });
        return out;
    }

    // Default rank: the owner's sort_order from the server; DEFAULT_ORDER when the metadata
    // lacks one (offline with no metadata saved yet)
    function defaultRank(src) {
        if (Number.isFinite(src.sort_order) && src.sort_order < 1000) return src.sort_order;
        const i = DEFAULT_ORDER.indexOf(src.slug);
        return i >= 0 ? (i + 1) * 10 : 1e4;
    }

    window.BibleStudyText = { analyzeEntry, entryOutline, whoLine, parseRefParts, mergeOrder };

    // IndexedDB can hold the same entry under an old key (source:book:ch:start) and a new
    // one (…:start-end); keep one of each, ordered by start then span.
    function dedupeRows(rows) {
        const seen = new Set();
        return rows.filter(r => {
            const k = `${r.reference_start}|${r.reference_end ?? ''}|${(r.content || '').length}`;
            if (seen.has(k)) return false;
            seen.add(k);
            return true;
        }).sort((a, b) => a.reference_start - b.reference_start
            || ((a.reference_end ?? a.reference_start) - (b.reference_end ?? b.reference_start)));
    }

    function verseLabel(s, e) {
        return s === e ? `v${s}` : `v${s}–${e}`;
    }

    window.BibleModules.study = {
        study: {
            open: false,
            loading: false,
            error: null,
            offline: false,
            ref: '', book: '', chapter: 0, vs: 0, ve: 0, chapterVerses: 0,
            verses: [],
            sources: [],          // all sources, server order, with availability
            active: null,         // slug of the source in view
            previous: null,       // slug of the source viewed before (quick swap)
            stripCollapsed: false,
            prevLabel: null,      // label of the study location Back returns to
            info: null,           // source shown in the info sheet
            peek: null,           // { ref, text, loading, error } for a reference tapped in commentary
            all: false,           // the "All" sheet: every enabled source and what it has here
            reveal: null,         // a hidden source opened by link: shown for this visit only
        },
        studyPrefsRev: 0,         // bumped on every save, so views that read the prefs re-render
        studyPanes: {},           // slug -> { status, html, note, focusCount }
        studyHint: null,
        studySourceMeta: [],      // every source's metadata (credits in search results, Settings > Commentaries)
        _studyDepth: 0,
        _studyOpener: null,
        _studyGen: 0,

        // ---------- lifecycle ----------
        studyInit() {
            // Esc / Android back on the open dialog: step back one study location
            document.getElementById('study-view')
                ?.addEventListener('cancel', (e) => { e.preventDefault(); this.studyBack(); });
            // Source metadata for credits outside the study view (search results)
            this.studySourceMeta = readJSON(META_KEY, []);
            fetch('/api/commentary/sources').then(r => r.ok ? r.json() : null).then(d => {
                if (d?.sources) { this.studySourceMeta = d.sources; writeJSON(META_KEY, d.sources); }
            }).catch(() => {});
            // The chip area narrows when the swap or Hymns button appears after the view has
            // placed the active chip (hymns load last): keep that chip in view
            const chips = document.querySelector('#study-view .study-chips');
            if (chips && window.ResizeObserver) {
                new ResizeObserver(() => this.study.open && this.studyRevealChip(this.study.active, false)).observe(chips);
            }
            // Settings > Commentaries opened from the study view: back to the study view after
            this.$watch('showSettings', (v) => { if (!v) this.studyResumeFromSettings(); });
            // Availability hint for the reader's selection (peek chip + action bar)
            this.$watch('highlightedVerses', () => this.studyRefreshHint());
            this.$watch('currentReference', () => this.studyRefreshHint());
        },

        // Per device, in localStorage (wrapped: with storage blocked, defaults apply)
        studyPrefs() {
            void this.studyPrefsRev;   // dependency: re-render when the prefs are saved
            const p = readJSON(PREFS_KEY, {}) || {};
            return { order: Array.isArray(p.order) ? p.order : [], hidden: Array.isArray(p.hidden) ? p.hidden : [], last: p.last || null };
        },
        studySavePrefs(p) { writeJSON(PREFS_KEY, p); this.studyPrefsRev++; },

        // Reader selection as a contiguous span: tapping 16 then 18 studies 16-18.
        studySelectionRef() {
            if (!this.currentBook || !this.currentChapter) return null;
            const vv = [...this.highlightedVerses].sort((a, b) => a - b);
            if (!vv.length) return `${this.currentBook} ${this.currentChapter}`;
            const [s, e] = [vv[0], vv[vv.length - 1]];
            return s === e ? `${this.currentBook} ${this.currentChapter}:${s}`
                : `${this.currentBook} ${this.currentChapter}:${s}-${e}`;
        },

        studyParseRef(ref) {
            const m = String(ref || '').trim().match(/^(.+?)\s+(\d+)(?::(\d+)(?:\s*[-–]\s*(\d+))?)?$/);
            if (!m) return null;
            const book = normalizeBookName(m[1]);
            const chapter = parseInt(m[2]);
            const vs = m[3] ? parseInt(m[3]) : null;
            const ve = m[4] ? Math.max(vs, parseInt(m[4])) : vs;
            return { book, chapter, vs, ve };
        },

        studyRefLabel(s = this.study) {
            if (!s.book) return '';
            if (!s.vs) return `${s.book} ${s.chapter}`;
            return s.vs === s.ve ? `${s.book} ${s.chapter}:${s.vs}` : `${s.book} ${s.chapter}:${s.vs}–${s.ve}`;
        },
        studyVersesLabel() {
            const s = this.study;
            if (!s.vs) return 'this chapter';
            return s.vs === s.ve ? `verse ${s.vs}` : `verses ${s.vs}–${s.ve}`;
        },

        studyURL(source = this.study.active) {
            const s = this.study;
            const slug = s.book.replace(/\s+/g, '-');
            const verses = s.vs ? (s.vs === s.ve ? `/${s.vs}` : `/${s.vs}-${s.ve}`) : '';
            return `/${slug}/${s.chapter}${verses}?study=${encodeURIComponent(source || '')}`;
        },

        // ---------- open / close / history ----------
        // history: 'push' (user opened), 'replace' (deep link, moving the selection), 'none' (popstate)
        async openStudy(ref = null, { source = null, history = 'push' } = {}) {
            ref = ref || this.studySelectionRef();
            const parsed = this.studyParseRef(ref);
            if (!parsed) return;
            const dlg = document.getElementById('study-view');
            const wasOpen = this.study.open;
            if (!wasOpen) {
                this._studyOpener = document.activeElement;
                if (this.ttsPlaying) this.ttsStop();
            }
            // Writing in progress is kept (saved for the verses it was written on; not awaited,
            // so nothing else can run between here and the new location's state)
            if (wasOpen) this.studyNotesFlush();
            const prevLabel = wasOpen && history === 'push' ? this.studyRefLabel() : null;
            const keepSource = source || (wasOpen ? this.study.active : null);

            Object.assign(this.study, {
                open: true, loading: true, error: null, book: parsed.book, chapter: parsed.chapter,
                vs: parsed.vs, ve: parsed.ve, peek: null, info: null, all: false, stripCollapsed: false,
            });
            if (!wasOpen) this.study.reveal = null;
            if (history === 'push') this.study.prevLabel = wasOpen ? prevLabel : null;
            if (dlg && !dlg.open) {
                dlg.showModal();
                document.documentElement.classList.add('study-open');
            }

            const gen = ++this._studyGen;
            const data = await this.studyLoadAvailability(parsed);
            if (gen !== this._studyGen) return;
            if (!data) {
                this.study.loading = false;
                this.study.error = this.isOnline && !this.forcedOffline
                    ? `Couldn't load ${this.studyRefLabel()}.`
                    : `${this.study.book} ${this.study.chapter} isn't saved for offline use. Open it once while online, or download it in Settings.`;
                return;
            }
            Object.assign(this.study, {
                loading: false, offline: data.offline, ref: data.reference,
                vs: data.verse_start, ve: data.verse_end, chapterVerses: data.chapter_verses,
                verses: data.verses, sources: data.sources,
            });
            // Whole-chapter study is shown as a range so the strip and steps work
            if (!parsed.vs) { this.study.vs = data.verse_start; this.study.ve = data.verse_end; }

            const prefs = this.studyPrefs();
            const want = [keepSource, prefs.last].map(x => x && slugify(x));
            // A link to a source the reader has turned off still opens it, for this visit
            if (source && want[0] && prefs.hidden.includes(want[0])) this.study.reveal = want[0];
            const track = this.studyTrack();
            // Cross-references and Notes open by name (deep link, the reader's Refs/Note
            // buttons); otherwise the asked-for or remembered source if it has something on
            // the selection, else the first source in the track that does. A deep link to a
            // source that no longer exists (?study=matthew-henry, removed 2026-11-13) lands
            // there too, and the URL is rewritten to the source shown.
            const active = (this.studyIsTool(want[0]) && want[0])
                || want.find(w => w && track.some(t => t.slug === w)) || track[0]?.slug || null;
            if (active !== this.study.active) this.study.previous = this.study.active || this.study.previous;
            this.study.active = active;

            // Selection changed: rebuild panes (cached chapter data makes this instant).
            // The track re-renders with other panes before it is scrolled to the active
            // one; that isn't the reader swiping.
            this._studyProgrammatic = Date.now();
            this.studyPanes = {};
            this.studyPanesReset();
            const url = this.studyURL(active);
            const depth = this._studyDepth;
            if (history === 'push') {
                this._studyDepth = depth + 1;
                this.navPushState({ study: true, studyDepth: this._studyDepth, studyPrevLabel: this.study.prevLabel }, url);
            } else if (history === 'replace') {
                this.navReplaceState({ study: true, studyDepth: depth, studyPrevLabel: this.study.prevLabel }, url);
            }

            this.$nextTick(() => {
                this.studyObservePanes();
                this.studyScrollToSource(active, false);
                if (active) {
                    if (!this.studyIsTool(active)) this.studyLoadPane(active);
                    this.studyRevealChip(active, false);
                }
                if (!wasOpen) document.getElementById('study-title')?.focus({ preventScroll: true });
            });
        },

        // Close the whole study view and return to the reader where it was opened.
        studyClose() {
            if (!this.study.open) return;
            if (this._studyDepth > 0) {
                window.history.go(-this._studyDepth);   // popstate hides the view
                return;
            }
            this.studyHide();
            this.updateURL();
        },

        // One step back: previous study location, or out to the reader.
        studyBack() {
            if (this.study.peek) { this.study.peek = null; return; }
            if (this._studyDepth > 0) window.history.back();
            else this.studyClose();
        },

        studyHide() {
            this.studyNotesFlush();
            this.studyWritingEnd();
            const dlg = document.getElementById('study-view');
            this.study.open = false;
            this.study.peek = null;
            this.study.info = null;
            this.study.all = false;
            this.study.reveal = null;
            this._studyResume = false;
            this._studyDepth = 0;
            this._studyGen++;
            if (paneObserver) { paneObserver.disconnect(); paneObserver = null; }
            dlg?.querySelectorAll('dialog[open]').forEach(d => d.close());
            if (dlg?.open) dlg.close();
            document.documentElement.classList.remove('study-open');
            const opener = this._studyOpener;
            this._studyOpener = null;
            if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
        },

        // Called first by the app's popstate handler (modules/nav.js). Returns true when
        // it showed a study entry, or closed the view onto the chapter already underneath.
        studyHandlePop(e) {
            const params = new URLSearchParams(window.location.search);
            if (params.has('study')) {
                this._studyDepth = e?.state?.studyDepth || 0;
                this.study.prevLabel = e?.state?.studyPrevLabel || null;
                this.openStudy(this.parsePathReference(), { source: params.get('study'), history: 'none' });
                return true;
            }
            if (!this.study.open) return false;
            this.studyHide();
            const ref = this.studyParseRef(this.parsePathReference());
            // Same chapter as the reader underneath: nothing to reload
            return !!ref && ref.book === this.currentBook && ref.chapter === this.currentChapter;
        },

        // ---------- data ----------
        async studyFetch(url) {
            if (this.forcedOffline) throw Object.assign(new Error('offline'), { offline: true });
            const r = await fetch(url);
            if (!r.ok) throw Object.assign(new Error(`HTTP ${r.status}`), { status: r.status, offline: r.status === 503 });
            return r.json();
        },

        async studyLoadAvailability({ book, chapter, vs, ve }) {
            const ref = vs ? (vs === ve ? `${book} ${chapter}:${vs}` : `${book} ${chapter}:${vs}-${ve}`) : `${book} ${chapter}`;
            try {
                const data = await this.studyFetch(`/api/passage/${encodeURIComponent(ref)}/study?translation=${encodeURIComponent(this.translation)}`);
                writeJSON(META_KEY, data.sources.map(({ selection_entries, chapter_entries, ranges, nearest, ...m }) => m));
                return { ...data, offline: false };
            } catch (err) {
                if (err.status && !err.offline) return null;   // server answered: bad reference
                return this.studyAvailabilityFromCache({ book, chapter, vs, ve });
            }
        },

        // Offline: verses + commentary from IndexedDB, metadata from the last online visit.
        async studyAvailabilityFromCache({ book, chapter, vs, ve }) {
            const os = window.offlineStorage;
            if (!os) return null;
            try {
                const verses = await os.getChapterVerses(this.translation, book, chapter);
                if (!verses?.length) return null;
                const last = verses[verses.length - 1].verse;
                const start = vs || 1;
                const end = Math.min(ve || last, last);
                const cached = await os.getChapterCommentary(book, chapter);
                const meta = readJSON(META_KEY, []);
                // The library as last seen online decides which sources exist: commentary a
                // device saved from a source since removed (Matthew Henry etc., 2026-11-13)
                // is not shown. With no metadata yet, show whatever was saved.
                const names = new Set(meta.length ? meta.map(m => m.source) : cached.map(c => c.source));
                const sources = [...names].map(name => {
                    const m = meta.find(x => x.source === name) || { source: name, slug: slugify(name), short_name: name, author: name, kind: 'verse', sort_order: 1000 };
                    const rows = dedupeRows(cached.filter(c => c.source === name));
                    const ranges = effectiveRanges(rows, m.kind, last);
                    const hits = ranges.filter(([s, e]) => s <= end && e >= start);
                    return {
                        ...m, selection_entries: hits.length, chapter_entries: rows.length,
                        ranges: hits.map(([s, e]) => ({ start: s, end: e })), nearest: null,
                        not_saved: rows.length === 0,
                    };
                });
                return {
                    reference: vs ? `${book} ${chapter}:${start}${end > start ? '-' + end : ''}` : `${book} ${chapter}`,
                    book, chapter, verse_start: start, verse_end: end, chapter_verses: last, offline: true,
                    verses: verses.filter(v => v.verse >= start && v.verse <= end).map(v => ({ verse: v.verse, text: v.text })),
                    sources,
                };
            } catch (e) {
                console.debug('study offline fallback failed', e);
                return null;
            }
        },

        async studyChapterEntries(src) {
            const { book, chapter } = this.study;
            const key = `${book}|${chapter}|${src.slug}`;
            if (chapterCache.has(key)) return chapterCache.get(key);
            let entries;
            try {
                const data = await this.studyFetch(`/api/passage/${encodeURIComponent(`${book} ${chapter}`)}/commentary?source=${encodeURIComponent(src.slug)}`);
                entries = data.entries || [];
                if (entries.length && window.offlineStorage) {
                    window.offlineStorage.saveChapterCommentary(book, chapter, entries).catch(() => {});
                }
            } catch (err) {
                if (err.status && !err.offline) throw err;
                const cached = window.offlineStorage ? await window.offlineStorage.getChapterCommentary(book, chapter) : [];
                const rows = dedupeRows((cached || []).filter(c => c.source === src.source));
                if (!rows.length) throw Object.assign(new Error('not saved'), { notSaved: true });
                const ranges = effectiveRanges(rows, src.kind, this.study.chapterVerses);
                entries = rows.map((r, i) => ({ ...r, range_start: ranges[i][0], range_end: ranges[i][1] }));
            }
            chapterCache.set(key, entries);
            return entries;
        },

        async studyLoadPane(slug) {
            const src = this.study.sources.find(s => s.slug === slug);
            if (!src || this.studyPanes[slug]?.status === 'ready' || this.studyPanes[slug]?.status === 'loading') return;
            const gen = this._studyGen;
            this.studyPanes[slug] = { status: 'loading', html: '', note: '', focusCount: 0 };
            try {
                const all = await this.studyChapterEntries(src);
                if (gen !== this._studyGen) return;
                const { vs, ve } = this.study;
                const entries = all.filter(e => e.range_start <= ve && e.range_end >= vs);
                this.studyPanes[slug] = { status: 'ready', ...this.studyRender(entries, src) };
                this.$nextTick(() => this.studyRevealFocus(slug, false));
            } catch (err) {
                if (gen !== this._studyGen) return;
                this.studyPanes[slug] = {
                    status: 'error', html: '', focusCount: 0,
                    note: err.notSaved ? `${src.short_name} isn't saved for offline use on this chapter.` : `Couldn't load ${src.short_name}. Check your connection and try again.`,
                };
            }
        },

        // ---------- rendering ----------
        // Lead with the entries that fit the selection (verse notes). A source's wider
        // entries (whole-psalm overview, passage note) follow as sections the reader opens.
        studyRender(entries, src) {
            const { book, chapter, vs, ve } = this.study;
            const ctx = { book, chapter, vs, ve };
            const selSpan = ve - vs;
            const tight = entries.filter(e => e.range_end - e.range_start <= selSpan);
            const lead = tight.length ? tight : entries;
            const extra = tight.length ? entries.filter(e => !tight.includes(e)) : [];
            let focusCount = 0;
            let note = '';
            let n = 0;
            const renderEntry = (entry, { heading }) => {
                const a = analyzeEntry(entry, ctx);
                const id = `se-${src.slug}-${n++}`;
                let entryFocus = 0;
                const body = a.paras.map((p, pi) => {
                    let html = sanitize(p.html);
                    let cls = '';
                    let mark = '';
                    if (p.marker) {
                        mark = `<span class="study-vmark" aria-label="Verse ${p.marker[0]}">${p.marker[0]}${p.marker[1] > p.marker[0] ? '–' + p.marker[1] : ''}</span>`;
                        cls = 'has-vmark';
                    } else {
                        const text = plain(html);
                        for (const [re, level] of OUTLINE) {
                            const m = text.match(re);
                            if (m && html.startsWith(m[1])) {
                                cls = `lvl lvl-${level}`;
                                mark = `<span class="study-mark" aria-hidden="true">${esc(m[1])}</span>`;
                                html = html.slice(m[0].length);
                                break;
                            }
                        }
                    }
                    if (pi === 0 && !mark) {
                        // Gill's lemma before ",...."; Scofield's headword line
                        html = html.replace(/^([^<]{3,240}?,?)\s?\.{3,4}/, '<span class="study-lemma">$1</span> ');
                        if (src.kind === 'notes' && a.paras.length > 1 && p.text.length < 60 && !/[.:;!?]$/.test(p.text)) cls = 'study-headword';
                    }
                    if (p.focus) { entryFocus++; cls += ' is-focus'; }
                    return `<p id="${id}-p${pi}" class="${cls.trim()}">${mark}${html}</p>`;
                }).join('');
                const outline = entryOutline(a);
                const toc = outline.length ? `<details class="study-toc"><summary>In this note: ${outline.length} parts</summary><ol>${outline.map(o => `<li><button type="button" data-jump="${id}-p${o.i}"><b>${esc(o.label)}</b> ${esc(o.hint)}</button></li>`).join('')}</ol></details>` : '';
                return { a, entryFocus, html: `<article class="study-entry">${heading ? `<h4 class="study-entry-range">${esc(heading)}</h4>` : ''}${toc}${body}</article>` };
            };
            const rangeLabel = (e) => e.range_start === e.range_end ? `Verse ${e.range_start}`
                : (e.range_start === 1 && e.range_end >= this.study.chapterVerses ? `${book} ${chapter}` : `Verses ${e.range_start}–${e.range_end}`);
            const parts = lead.map(entry => {
                const showHeading = lead.length > 1 || entry.range_end > entry.range_start || src.kind !== 'verse' || extra.length;
                const r = renderEntry(entry, { heading: showHeading ? rangeLabel(entry) : null });
                focusCount += r.entryFocus;
                if (r.a.wide && !note) {
                    const span = r.a.rs === 1 && r.a.re >= this.study.chapterVerses
                        ? `the whole of ${book} ${chapter}` : `${book} ${chapter}:${r.a.rs}–${r.a.re}`;
                    const what = r.a.mode === 'markers' ? `The part on ${this.studyVersesLabel()} is marked.`
                        : `The ${r.entryFocus === 1 ? 'paragraph that mentions' : `${r.entryFocus} paragraphs that mention`} ${this.studyVersesLabel()} ${r.entryFocus === 1 ? 'is' : 'are'} marked.`;
                    note = r.entryFocus ? `This note covers ${span}. ${what}`
                        : `This note covers ${span} and doesn't single out ${this.studyVersesLabel()}; read it as context.`;
                }
                return r.html;
            });
            const unit = book === 'Psalms' ? 'psalm' : 'chapter';
            const more = extra.map(entry => {
                const whole = entry.range_start === 1 && entry.range_end >= this.study.chapterVerses;
                const label = whole ? `${src.short_name}'s note on the whole ${unit}`
                    : `${src.short_name}'s note on verses ${entry.range_start}–${entry.range_end}`;
                const r = renderEntry(entry, { heading: null });
                // Opening words tell two overviews from the same source apart
                const opening = r.a.paras[0]?.text.replace(/\s+/g, ' ').slice(0, 70) || '';
                return `<details class="study-more"><summary><span>${esc(label)}<span class="study-more-hint">${esc(opening)}…</span></span></summary>${r.html}</details>`;
            });
            return { html: parts.join('') + more.join(''), note, focusCount };
        },

        // Scroll a pane to its next marked paragraph (wraps around).
        studyRevealFocus(slug, step = true) {
            const pane = document.querySelector(`.study-pane[data-slug="${CSS.escape(slug)}"] .study-pane-scroll`);
            if (!pane) return;
            const marks = [...pane.querySelectorAll('p.is-focus')];
            if (!marks.length) return;
            const state = this.studyPanes[slug];
            const i = step ? ((state.focusIndex ?? -1) + 1) % marks.length : 0;
            state.focusIndex = i;
            const top = marks[i].offsetTop - 16;
            if (!step) this._studyAutoScroll = Date.now();
            pane.scrollTo({ top: Math.max(0, top), behavior: step && !reduceMotion() ? 'smooth' : 'auto' });
        },

        // ---------- sources: order, availability, switching ----------
        // Any list of sources (study.sources, or the metadata for Settings) in the reader's order
        studyOrderOf(list) {
            const defaults = [...list].sort((a, b) => defaultRank(a) - defaultRank(b)
                || String(a.source).localeCompare(String(b.source))).map(s => s.slug);
            const order = mergeOrder(this.studyPrefs().order, defaults);
            const bySlug = new Map(list.map(s => [s.slug, s]));
            return order.map(slug => bySlug.get(slug));
        },
        // Turned-off sources that exist. If every one is off (an old device, or a library
        // that changed under it), none are: the study view never ends up with no sources.
        studyHiddenOf(list) {
            const slugs = new Set(list.map(s => s.slug));
            const hidden = new Set(this.studyPrefs().hidden.filter(h => slugs.has(h)));
            if (hidden.size >= slugs.size) hidden.clear();
            return hidden;
        },
        studyOrdered() { return this.studyOrderOf(this.study.sources); },
        // Sources the reader reads: the rail, the swipe order and the All sheet
        studyEnabled() {
            const hidden = this.studyHiddenOf(this.study.sources);
            return this.studyOrdered().filter(s => !hidden.has(s.slug) || s.slug === this.study.reveal);
        },
        // The ones with something on the selection: chips and panes
        studyTrack() { return this.studyEnabled().filter(s => s.selection_entries > 0); },
        studyEmpty() { return this.studyEnabled().filter(s => !(s.selection_entries > 0)); },
        studyActiveSource() {
            return this.study.sources.find(s => s.slug === this.study.active) || null;
        },
        studySourceBySlug(slug) {
            return this.study.sources.find(s => s.slug === slug) || null;
        },

        // How targeted a source is on this selection, shown on its chip.
        // Label a chip by the tightest match: a verse note beats the same source's overview.
        studyChipScope(src) {
            if (src.not_saved) return 'not saved';
            if (!(src.selection_entries > 0)) return 'nothing here';
            const all = src.ranges || [];
            const selSpan = this.study.ve - this.study.vs;
            const tight = all.filter(x => x.end - x.start <= selSpan);
            const r = tight.length ? tight : all;
            const lo = Math.min(...r.map(x => x.start)); const hi = Math.max(...r.map(x => x.end));
            if (lo <= 1 && hi >= this.study.chapterVerses && this.study.chapterVerses > 1
                && !(this.study.vs <= 1 && this.study.ve >= this.study.chapterVerses)) return 'chapter';
            return verseLabel(lo, hi);
        },
        studyChipLabel(src) {
            return `${src.source}: ${this.studyChipScope(src)}`;
        },

        studySelect(slug, { scroll = true } = {}) {
            if (!slug) return;
            const tool = this.studyIsTool(slug);
            const src = tool ? null : this.studySourceBySlug(slug);
            if (!tool && !src) return;
            if (src && !(src.selection_entries > 0)) { this.studyShowInfo(slug); return; }
            if (slug !== this.study.active) {
                // The swap button goes back to the last commentary source
                if (!this.studyIsTool(this.study.active)) this.study.previous = this.study.active;
                this.study.active = slug;
                if (!tool) this.studySavePrefs({ ...this.studyPrefs(), last: slug });
                if (slug === 'notes') this.study.stripCollapsed = false;   // write with the verses in view
                if (this.study.open) this.navReplaceState({ ...(window.history.state || {}), study: true }, this.studyURL(slug));
            }
            this.studyLoadPane(slug);
            if (scroll) this.studyScrollToSource(slug, true);
            this.studyRevealChip(slug, true);
        },

        // Scroll the chip row (only the row, nothing around it) so the active chip is fully
        // in view with a margin. After layout: the row's width and contents change as the
        // view settles (swap and Hymns buttons appear, chips re-render).
        studyRevealChip(slug, smooth = false) {
            if (!slug || this.studyIsTool(slug)) return;
            this.$nextTick(() => requestAnimationFrame(() => {
                const row = document.querySelector('#study-view .study-chips');
                const chip = row?.querySelector(`.study-chip[data-slug="${CSS.escape(slug)}"]`);
                if (!chip || !row.clientWidth) return;
                const box = row.getBoundingClientRect();
                const r = chip.getBoundingClientRect();
                let dx = 0;
                // Too wide for the margins (a narrow row): centred
                if (r.width > box.width - 2 * CHIP_MARGIN) dx = (r.left + r.right - box.left - box.right) / 2;
                else if (r.left < box.left + CHIP_MARGIN) dx = r.left - box.left - CHIP_MARGIN;
                else if (r.right > box.right - CHIP_MARGIN) dx = r.right - box.right + CHIP_MARGIN;
                if (Math.abs(dx) < 1) return;
                row.scrollBy({ left: dx, behavior: smooth && !reduceMotion() ? 'smooth' : 'auto' });
            }));
        },

        studySwap() {
            if (this.study.previous && this.studyTrack().some(s => s.slug === this.study.previous)) {
                this.studySelect(this.study.previous);
            }
        },

        studyScrollToSource(slug, smooth) {
            const track = document.querySelector('.study-track');
            const pane = slug && track?.querySelector(`.study-pane[data-slug="${CSS.escape(slug)}"]`);
            if (!pane) return;
            this._studyProgrammatic = Date.now();
            track.scrollTo({ left: pane.offsetLeft, behavior: smooth && !reduceMotion() ? 'smooth' : 'auto' });
        },

        // Swipe sync: the pane that fills the track becomes active; neighbours prefetch.
        studyObservePanes() {
            if (paneObserver) paneObserver.disconnect();
            const track = document.querySelector('.study-track');
            if (!track) return;
            paneObserver = new IntersectionObserver((entries) => {
                for (const en of entries) {
                    const slug = en.target.dataset.slug;
                    if (en.isIntersecting) this.studyLoadPane(slug);
                    // Leftmost (mostly) visible pane is the active one
                    // Not while a new location loads or the view places itself: panes come and
                    // go then, and the scroll position moves without the reader swiping
                    if (en.intersectionRatio >= 0.6 && !this.study.loading && Date.now() - (this._studyProgrammatic || 0) > 600) {
                        const visible = [...track.querySelectorAll('.study-pane')].filter(p => {
                            const r = p.getBoundingClientRect(); const t = track.getBoundingClientRect();
                            return r.left >= t.left - 4 && r.left < t.right - 40;
                        });
                        const first = visible[0]?.dataset.slug;
                        if (first && first !== this.study.active) this.studySelect(first, { scroll: false });
                    }
                }
            }, { root: track, threshold: [0, 0.6] });
            track.querySelectorAll('.study-pane').forEach(p => paneObserver.observe(p));
        },

        studyPaneScrolled(event) {
            // Only the reader's own scrolling hides the verses, never our jump to the marked part
            if (isWide() || Date.now() - (this._studyAutoScroll || 0) < 800) return;
            const y = event.target.scrollTop;
            if (y > 120 && !this.study.stripCollapsed) this.study.stripCollapsed = true;
        },

        // ---------- moving the selection ----------
        studyStep(dir) {
            const { book, chapter, vs, ve, chapterVerses } = this.study;
            const width = ve - vs;
            let s = vs + dir * (width + 1);
            if (s < 1 || s > chapterVerses) return;
            const e = Math.min(s + width, chapterVerses);
            this.openStudy(`${book} ${chapter}:${s}-${e}`, { history: 'replace' });
        },
        studyExtend(dir) {
            const { book, chapter, chapterVerses } = this.study;
            let { vs, ve } = this.study;
            if (dir < 0 && vs > 1) vs--;
            else if (dir > 0 && ve < chapterVerses) ve++;
            else return;
            this.openStudy(`${book} ${chapter}:${vs}-${ve}`, { history: 'replace' });
        },

        // ---------- source info ----------
        studyShowInfo(slug) {
            this.study.info = this.studySourceBySlug(slug || this.study.active);
            this.$nextTick(() => document.getElementById('study-info')?.showModal());
        },
        studyCloseInfo() {
            document.getElementById('study-info')?.close();
            this.study.info = null;
        },
        // The credit a source's license requires, wherever its text appears ('' if none)
        studyCredit(sourceName) {
            const m = (this.studySourceMeta || []).find(s => s.source === sourceName);
            return m?.requires_attribution ? (m.attribution || m.license || '') : '';
        },
        studyKindLabel(kind) { return KIND_LABEL[kind] || ''; },
        studyWho(src) { return src ? whoLine(src) : {}; },
        studyStudyNearest(src) {
            const n = src?.nearest;
            this.studyCloseInfo();
            if (n) this.openStudy(`${this.study.book} ${this.study.chapter}:${n.start}-${n.end}`, { source: src.slug, history: 'push' });
        },

        // ---------- the All sheet: every enabled source and what it has here ----------
        studyOpenAll() {
            this.study.all = true;
            this.$nextTick(() => {
                const dlg = document.getElementById('study-all');
                if (!dlg || dlg.open) return;
                dlg.showModal();
                // Start on the active source's row (the browser would pick the close button)
                (dlg.querySelector('.study-all-item[aria-current="true"]') || dlg.querySelector('.study-all-item'))
                    ?.focus({ preventScroll: false });
            });
        },
        studyCloseAll() {
            document.getElementById('study-all')?.close();
        },
        // The dialog's close event (Done, Escape, Android back, a choice): focus back on All
        studyAllClosed() {
            this.study.all = false;
            if (this.study.open && !this._studyResume) document.querySelector('#study-view .study-all-btn')?.focus({ preventScroll: true });
        },
        studyAllPick(slug) {
            this.studyCloseAll();
            this.studySelect(slug);
        },
        studyAllNearest(src) {
            const n = src?.nearest;
            this.studyCloseAll();
            if (n) this.openStudy(`${this.study.book} ${this.study.chapter}:${n.start}-${n.end}`, { source: src.slug, history: 'push' });
        },
        // What a source has on the selection, in words, for the All sheet
        studyAllScope(src) {
            if (src.not_saved) return "Not saved for offline use";
            if (!(src.selection_entries > 0)) return 'Nothing here';
            const scope = this.studyChipScope(src);
            if (scope === 'chapter') return `On the whole ${this.study.book === 'Psalms' ? 'psalm' : 'chapter'}`;
            const m = scope.match(/^v(\d+)(?:–(\d+))?$/);
            if (!m) return scope;
            const lo = +m[1]; const hi = m[2] ? +m[2] : lo;
            return lo === hi ? `Verse note, verse ${lo}` : `Passage note, verses ${lo}–${hi}`;
        },
        studyNearestLabel(n) { return n.start === n.end ? `verse ${n.start}` : `verses ${n.start}–${n.end}`; },

        // ---------- Settings > Commentaries (per device) ----------
        // From the study view: the view steps aside (Settings isn't in the top layer) and
        // comes back where it was when Settings closes, with the changes applied.
        studyChooseSources() {
            this._studyResume = this.study.open;
            this.studyCloseAll();
            document.getElementById('study-view')?.close();
            this.openSettings('commentaries');
            this.$nextTick(() => {
                const tab = document.querySelector('.settings-modal .settings-nav-btn.active');
                tab?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
                tab?.focus({ preventScroll: true });
            });
        },
        studyResumeFromSettings() {
            if (!this._studyResume) return;
            this._studyResume = false;
            if (!this.study.open) return;   // the reader went elsewhere meanwhile
            // The track re-renders and is placed below; that isn't the reader swiping
            this._studyProgrammatic = Date.now();
            const dlg = document.getElementById('study-view');
            if (dlg && !dlg.open) dlg.showModal();
            // The source in view was turned off: the first one left that has something here
            if (!this.studyIsTool(this.study.active) && !this.studyTrack().some(s => s.slug === this.study.active)) {
                const next = this.studyTrack()[0]?.slug || null;
                if (next) this.studySelect(next, { scroll: false });
                else this.study.active = null;
            }
            this.$nextTick(() => {
                this.studyObservePanes();
                this.studyScrollToSource(this.study.active, false);
                this.studyRevealChip(this.study.active, false);
                document.querySelector('#study-view .study-all-btn')?.focus({ preventScroll: true });
            });
        },
        // Every source in the library, in the reader's order (metadata: works without a study open)
        studySettingsSources() {
            const meta = (this.studySourceMeta || []).filter(m => m && m.slug);
            return meta.length ? this.studyOrderOf(meta) : [];
        },
        studySettingsHidden() { return this.studyHiddenOf(this.studySettingsSources()); },
        studyIsHidden(slug) { return this.studySettingsHidden().has(slug); },
        // The last source still on can't be turned off
        studyIsLastShown(slug) {
            const list = this.studySettingsSources();
            const hidden = this.studySettingsHidden();
            return !hidden.has(slug) && list.length - hidden.size <= 1;
        },
        studyMove(slug, dir) {
            const order = this.studySettingsSources().map(s => s.slug);
            const i = order.indexOf(slug); const j = i + dir;
            if (i < 0 || j < 0 || j >= order.length) return;
            [order[i], order[j]] = [order[j], order[i]];
            this.studySavePrefs({ ...this.studyPrefs(), order });
            // Keep focus on the arrow pressed; at the end of the list, on the other one
            this.$nextTick(() => {
                const btn = document.querySelector(`[data-move="${CSS.escape(slug)}:${dir}"]`);
                (btn && !btn.disabled ? btn : document.querySelector(`[data-move="${CSS.escape(slug)}:${-dir}"]`))?.focus();
            });
        },
        studyToggleHidden(slug) {
            if (this.studyIsLastShown(slug)) return;
            const prefs = this.studyPrefs();
            const hidden = this.studySettingsHidden();
            hidden.has(slug) ? hidden.delete(slug) : hidden.add(slug);
            this.studySavePrefs({ ...prefs, hidden: [...hidden] });
        },
        studyResetSources() {
            const { last } = this.studyPrefs();
            this.studySavePrefs({ order: [], hidden: [], last });
        },
        // "John Gill (1697–1771) · 1746 · Baptist (Particular Baptist)"
        studyMetaLine(src) {
            const author = String(src.author || '').replace(/(\d)-(\d)/g, '$1–$2');
            return [author, src.year, src.tradition].filter(Boolean).join(' · ');
        },
        // First sentence of the description
        studyBlurb(src) {
            const d = String(src.description || '');
            const m = d.match(/^.*?[.!?](?=\s|$)/);
            return m ? m[0] : d;
        },

        // ---------- references inside commentary ----------
        async studyContentClick(event) {
            const jump = event.target.closest('[data-jump]');
            if (jump) {
                const target = document.getElementById(jump.dataset.jump);
                const pane = target?.closest('.study-pane-scroll');
                if (pane) pane.scrollTo({ top: Math.max(0, target.offsetTop - 16), behavior: reduceMotion() ? 'auto' : 'smooth' });
                return;
            }
            const link = event.target.closest('.commentary-ref');
            if (!link) return;
            event.preventDefault();
            this.studyPeek(link.dataset.ref);
        },

        // A reference in a sheet over the study view: read it, study it, or go and read it.
        // context: also show two verses either side, dimmed (cross-references: the verse
        // itself is already on screen, what the reader lacks is where it sits).
        async studyPeek(ref, { context = false } = {}) {
            const parsed = this.studyParseRef(ref);
            if (!parsed) return;
            const token = Symbol('peek');
            this.study.peek = { ref, token, text: [], loading: true, error: null, focus: null };
            this.$nextTick(() => document.getElementById('study-peek')?.showModal());
            const { book, chapter } = parsed;
            let { vs, ve } = parsed;
            const ask = context && vs
                ? `${book} ${chapter}:${Math.max(1, vs - 2)}-${ve + 2}` : ref;
            if (context && vs) this.study.peek.focus = [vs, ve];
            if (context && vs) { vs = Math.max(1, vs - 2); ve += 2; }
            const inRange = v => !vs || (v.verse >= vs && v.verse <= ve);
            let verses = null;
            try {
                const data = await this.studyFetch(`/api/passage/${encodeURIComponent(ask)}/study?translation=${encodeURIComponent(this.translation)}`);
                verses = data.verses;
                if (this.study.peek?.token === token && !context) this.study.peek.ref = data.reference;
            } catch {
                try {
                    const cached = await window.offlineStorage?.getChapterVerses(this.translation, book, chapter);
                    if (cached?.length) verses = cached.filter(inRange).map(v => ({ verse: v.verse, text: v.text }));
                } catch { /* fall through */ }
            }
            if (this.study.peek?.token !== token) return;   // closed or replaced meanwhile
            this.study.peek.loading = false;
            if (verses?.length) this.study.peek.text = vs ? verses : verses.slice(0, 3);
            else this.study.peek.error = navigator.onLine ? `Couldn't find ${ref}.` : `${ref} isn't saved for offline use.`;
        },
        studyClosePeek() {
            document.getElementById('study-peek')?.close();
            this.study.peek = null;
        },
        studyPeekStudy() {
            const ref = this.study.peek?.ref;
            this.studyClosePeek();
            if (ref) this.openStudy(ref, { history: 'push' });
        },
        // Leave the study view for the reader; the return chip and Back both come back
        // to this study location (navigate() closes the view).
        studyPeekRead() {
            const ref = this.study.peek?.ref;
            this.studyClosePeek();
            if (ref) this.navigate(ref, { kind: 'jump' });
        },

        // ---------- reader hint: which sources say something on the selection ----------
        async studyRefreshHint() {
            const ref = this.highlightedVerses.length ? this.studySelectionRef() : null;
            if (!ref) { this.studyHint = null; return; }
            if (this.studyHint?.key === ref) return;
            clearTimeout(this._studyHintTimer);
            this._studyHintTimer = setTimeout(async () => {
                const parsed = this.studyParseRef(ref);
                if (!parsed) return;
                const data = await this.studyLoadAvailability(parsed);
                if (this.studySelectionRef() !== ref) return;
                const hidden = new Set(this.studyPrefs().hidden);
                const visible = (data?.sources || []).filter(s => !hidden.has(s.slug));
                this.studyHint = data ? {
                    key: ref,
                    withComment: visible.filter(s => s.selection_entries > 0),
                    total: visible.length,
                } : null;
            }, 200);
        },
    };
})();
