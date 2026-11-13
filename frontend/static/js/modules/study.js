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
            manage: false,
        },
        studyPanes: {},           // slug -> { status, html, note, focusCount }
        studyHint: null,          // { key, withComment, total } for the reader's selection
        _studyDepth: 0,
        _studyOpener: null,
        _studyGen: 0,

        // ---------- lifecycle ----------
        studyInit() {
            const dlg = document.getElementById('study-view');
            if (dlg) {
                // Esc / Android back on the open dialog: step back one study location
                dlg.addEventListener('cancel', (e) => { e.preventDefault(); this.studyBack(); });
            }
            // Availability hint for the reader's selection (peek chip + action bar)
            this.$watch('highlightedVerses', () => this.studyRefreshHint());
            this.$watch('currentReference', () => this.studyRefreshHint());
        },

        studyPrefs() {
            const p = readJSON(PREFS_KEY, {});
            return { order: Array.isArray(p.order) ? p.order : [], hidden: Array.isArray(p.hidden) ? p.hidden : [], last: p.last || null };
        },
        studySavePrefs(p) { writeJSON(PREFS_KEY, p); },

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
            const prevLabel = wasOpen && history === 'push' ? this.studyRefLabel() : null;
            const keepSource = source || (wasOpen ? this.study.active : null);

            Object.assign(this.study, {
                open: true, loading: true, error: null, book: parsed.book, chapter: parsed.chapter,
                vs: parsed.vs, ve: parsed.ve, peek: null, info: null, manage: false, stripCollapsed: false,
            });
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

            const track = this.studyTrack();
            const prefs = this.studyPrefs();
            const want = [keepSource, prefs.last].map(x => x && slugify(x));
            const active = want.find(w => w && track.some(t => t.slug === w)) || track[0]?.slug || null;
            if (active !== this.study.active) this.study.previous = this.study.active || this.study.previous;
            this.study.active = active;

            // Selection changed: rebuild panes (cached chapter data makes this instant)
            this.studyPanes = {};
            const url = this.studyURL(active);
            const depth = this._studyDepth;
            if (history === 'push') {
                this._studyDepth = depth + 1;
                window.history.pushState({ study: true, studyDepth: this._studyDepth, studyPrevLabel: this.study.prevLabel }, '', url);
            } else if (history === 'replace') {
                window.history.replaceState({ study: true, studyDepth: depth, studyPrevLabel: this.study.prevLabel }, '', url);
            }

            this.$nextTick(() => {
                this.studyObservePanes();
                this.studyScrollToSource(active, false);
                if (active) this.studyLoadPane(active);
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
            this.updateURL(false);
        },

        // One step back: previous study location, or out to the reader.
        studyBack() {
            if (this.study.peek) { this.study.peek = null; return; }
            if (this._studyDepth > 0) window.history.back();
            else this.studyClose();
        },

        studyHide() {
            const dlg = document.getElementById('study-view');
            this.study.open = false;
            this.study.peek = null;
            this.study.info = null;
            this.study.manage = false;
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

        // Called first by the app's popstate handler. Returns true when handled.
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
                const names = new Set([...meta.map(m => m.source), ...cached.map(c => c.source)]);
                const sources = [...names].map(name => {
                    const m = meta.find(x => x.source === name) || { source: name, slug: slugify(name), short_name: name, author: name, kind: 'verse', sort_order: 1000 };
                    const rows = cached.filter(c => c.source === name).sort((a, b) => a.reference_start - b.reference_start);
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
                const rows = (cached || []).filter(c => c.source === src.source).sort((a, b) => a.reference_start - b.reference_start);
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
        studyRender(entries, src) {
            const { book, chapter, vs, ve } = this.study;
            let focusCount = 0;
            let note = '';
            const mentions = (text, html) => {
                // data-ref links to this chapter, or "ver. 16", "v. 16", "verse 16", "vv. 16-18"
                for (const m of html.matchAll(/data-ref="([^"]+)"/g)) {
                    const r = this.studyParseRef(m[1]);
                    if (r && r.book === book && r.chapter === chapter && r.vs && r.vs <= ve && (r.ve || r.vs) >= vs) return true;
                }
                for (const m of text.matchAll(/\b(?:verses?|vers?\.|vv?\.)\s*(\d+)(?:\s*[-–]\s*(\d+))?/gi)) {
                    const a = parseInt(m[1]); const b = m[2] ? parseInt(m[2]) : a;
                    if (a <= ve && b >= vs) return true;
                }
                return false;
            };
            const parts = entries.map((entry, idx) => {
                const wide = entry.range_end - entry.range_start > ve - vs;
                const paras = String(entry.content || '').split(/\n+/).map(p => p.trim()).filter(Boolean);
                let entryFocus = 0;
                const body = paras.map((raw, pi) => {
                    let html = sanitize(raw);
                    const text = html.replace(/<[^>]*>/g, '');
                    let cls = '';
                    let mark = '';
                    for (const [re, level] of OUTLINE) {
                        const m = text.match(re);
                        if (m && html.startsWith(m[1])) {
                            cls = `lvl lvl-${level}`;
                            mark = `<span class="study-mark" aria-hidden="true">${esc(m[1])}</span>`;
                            html = html.slice(m[0].length);
                            break;
                        }
                    }
                    // Gill-style lemma: the quoted text before ",...."
                    if (pi === 0 && !mark) html = html.replace(/^([^<]{3,240}?,?)\s?\.{3,4}/, '<span class="study-lemma">$1</span> ');
                    const focus = wide && mentions(text, raw);
                    if (focus) { entryFocus++; cls += ' is-focus'; }
                    return `<p class="${cls.trim()}">${mark}${html}</p>`;
                }).join('');
                focusCount += entryFocus;
                if (wide && !note) {
                    const span = entry.range_start === 1 && entry.range_end >= this.study.chapterVerses
                        ? `the whole of ${book} ${chapter}` : `${book} ${chapter}:${entry.range_start}–${entry.range_end}`;
                    note = entryFocus
                        ? `This note covers ${span}. The ${entryFocus === 1 ? 'paragraph' : `${entryFocus} paragraphs`} about ${this.studyVersesLabel()} ${entryFocus === 1 ? 'is' : 'are'} marked.`
                        : `This note covers ${span} and doesn't single out ${this.studyVersesLabel()}; read it as context.`;
                }
                const heading = entry.range_start === entry.range_end ? `Verse ${entry.range_start}`
                    : (entry.range_start === 1 && entry.range_end >= this.study.chapterVerses ? `${book} ${chapter}` : `Verses ${entry.range_start}–${entry.range_end}`);
                const showHeading = entries.length > 1 || wide || src.kind !== 'verse';
                return `<article class="study-entry" data-entry="${idx}">${showHeading ? `<h4 class="study-entry-range">${esc(heading)}</h4>` : ''}${body}</article>`;
            });
            return { html: parts.join(''), note, focusCount };
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
            pane.scrollTo({ top: Math.max(0, top), behavior: step && !reduceMotion() ? 'smooth' : 'auto' });
        },

        // ---------- sources: order, availability, switching ----------
        studyOrdered() {
            const prefs = this.studyPrefs();
            const rank = new Map(prefs.order.map((s, i) => [s, i]));
            return this.study.sources
                .map((s, i) => ({ s, i }))
                .sort((a, b) => (rank.has(a.s.slug) ? rank.get(a.s.slug) : 1e4 + a.i) - (rank.has(b.s.slug) ? rank.get(b.s.slug) : 1e4 + b.i))
                .map(x => x.s);
        },
        studyTrack() {
            const hidden = new Set(this.studyPrefs().hidden);
            return this.studyOrdered().filter(s => !hidden.has(s.slug) && s.selection_entries > 0);
        },
        studyEmpty() {
            const hidden = new Set(this.studyPrefs().hidden);
            return this.studyOrdered().filter(s => !hidden.has(s.slug) && !(s.selection_entries > 0));
        },
        studyActiveSource() {
            return this.study.sources.find(s => s.slug === this.study.active) || null;
        },
        studySourceBySlug(slug) {
            return this.study.sources.find(s => s.slug === slug) || null;
        },

        // How targeted a source is on this selection, shown on its chip.
        studyChipScope(src) {
            if (src.not_saved) return 'not saved';
            if (!(src.selection_entries > 0)) return 'nothing here';
            const r = src.ranges || [];
            if (src.kind === 'chapter' || (r[0] && r[0].start === 1 && r[0].end >= this.study.chapterVerses)) return 'chapter';
            if (r.length === 1) return verseLabel(r[0].start, r[0].end);
            const lo = Math.min(...r.map(x => x.start)); const hi = Math.max(...r.map(x => x.end));
            return verseLabel(lo, hi);
        },
        studyChipLabel(src) {
            return `${src.author}${src.year ? `, ${src.year}` : ''}: ${this.studyChipScope(src)}`;
        },

        studySelect(slug, { scroll = true } = {}) {
            if (!slug) return;
            const src = this.studySourceBySlug(slug);
            if (!src) return;
            if (!(src.selection_entries > 0)) { this.studyShowInfo(slug); return; }
            if (slug !== this.study.active) {
                this.study.previous = this.study.active;
                this.study.active = slug;
                const prefs = this.studyPrefs();
                this.studySavePrefs({ ...prefs, last: slug });
                if (this.study.open) window.history.replaceState({ ...(window.history.state || {}), study: true }, '', this.studyURL(slug));
            }
            this.studyLoadPane(slug);
            if (scroll) this.studyScrollToSource(slug, true);
            this.$nextTick(() => document.querySelector(`.study-chip[data-slug="${CSS.escape(slug)}"]`)
                ?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: reduceMotion() ? 'auto' : 'smooth' }));
        },

        studySwap() {
            if (this.study.previous && this.studySourceBySlug(this.study.previous)?.selection_entries > 0) {
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
                    if (en.intersectionRatio >= 0.6 && Date.now() - (this._studyProgrammatic || 0) > 600) {
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
            if (isWide()) return;
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

        // ---------- source info + manage ----------
        studyShowInfo(slug) {
            this.study.info = this.studySourceBySlug(slug || this.study.active);
            this.$nextTick(() => document.getElementById('study-info')?.showModal());
        },
        studyCloseInfo() {
            document.getElementById('study-info')?.close();
            this.study.info = null;
        },
        studyKindLabel(kind) { return KIND_LABEL[kind] || ''; },
        studyStudyNearest(src) {
            const n = src?.nearest;
            this.studyCloseInfo();
            if (n) this.openStudy(`${this.study.book} ${this.study.chapter}:${n.start}-${n.end}`, { source: src.slug, history: 'push' });
        },

        studyOpenManage() {
            this.study.manage = true;
            this.$nextTick(() => document.getElementById('study-manage')?.showModal());
        },
        studyCloseManage() {
            document.getElementById('study-manage')?.close();
            this.study.manage = false;
            this.$nextTick(() => this.studyObservePanes());
        },
        studyMove(slug, dir) {
            const order = this.studyOrdered().map(s => s.slug);
            const i = order.indexOf(slug); const j = i + dir;
            if (i < 0 || j < 0 || j >= order.length) return;
            [order[i], order[j]] = [order[j], order[i]];
            this.studySavePrefs({ ...this.studyPrefs(), order });
            this.study.sources = [...this.study.sources];   // re-render order
            this.$nextTick(() => {
                document.querySelector(`#study-manage [data-move="${CSS.escape(slug)}:${dir}"]`)?.focus();
                this.studyScrollToSource(this.study.active, false);
            });
        },
        studyIsHidden(slug) { return this.studyPrefs().hidden.includes(slug); },
        studyToggleHidden(slug) {
            const prefs = this.studyPrefs();
            const hidden = new Set(prefs.hidden);
            hidden.has(slug) ? hidden.delete(slug) : hidden.add(slug);
            this.studySavePrefs({ ...prefs, hidden: [...hidden] });
            this.study.sources = [...this.study.sources];
            if (hidden.has(slug) && this.study.active === slug) {
                this.study.active = this.studyTrack()[0]?.slug || null;
                if (this.study.active) this.studyLoadPane(this.study.active);
            }
        },
        studyResetOrder() {
            this.studySavePrefs({ ...this.studyPrefs(), order: [], hidden: [] });
            this.study.sources = [...this.study.sources];
        },

        // ---------- references inside commentary ----------
        async studyContentClick(event) {
            const link = event.target.closest('.commentary-ref');
            if (!link) return;
            event.preventDefault();
            const ref = link.dataset.ref;
            const parsed = this.studyParseRef(ref);
            if (!parsed) return;
            const token = Symbol('peek');
            this.study.peek = { ref, token, text: [], loading: true, error: null };
            this.$nextTick(() => document.getElementById('study-peek')?.showModal());
            const { book, chapter, vs, ve } = parsed;
            const inRange = v => !vs || (v.verse >= vs && v.verse <= ve);
            let verses = null;
            try {
                const data = await this.studyFetch(`/api/passage/${encodeURIComponent(ref)}/study?translation=${encodeURIComponent(this.translation)}`);
                verses = data.verses;
                if (this.study.peek?.token === token) this.study.peek.ref = data.reference;
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
        // Leave the study view for the reader; Back returns to this study location.
        studyPeekRead() {
            const ref = this.study.peek?.ref;
            this.studyClosePeek();
            if (!ref) return;
            this.studyHide();
            this.loadReference(ref);
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
