// bibleApp feature module: hymns — the study view's Hymns pane and a hymn's sheet.
// Merged via Object.assign in app.js. Markup: the hymns .study-pane, its rail button
// and <dialog id="study-hymn"> in <dialog id="study-view"> (index.html); styles in
// css/study.css. Data: GET /api/hymns/for-passage and /api/hymns/{id}
// (docs/HYMN_INDEX_2026-11.md).
//
// The pane answers "which hymns are built on these verses": the hymns linked to the
// selection first, then (apart, and labelled) those linked elsewhere in its chapter.
// Each says why it is linked, in the source's own terms; a computed quotation shows the
// shared words and says it is computed. The index is incomplete by nature (public-domain
// hymnals only), so the pane says so, and a passage with no hymns has no pane at all.
window.BibleModules = window.BibleModules || {};
(() => {
    const SOURCE_SHORT = {
        openhymnal: 'the Open Hymnal', 'openhymnal-credit': 'the Open Hymnal',
        'pg-watts-psalms': "Watts' Psalms of David (1719)", 'pg-watts-hss': "Watts' Hymns and Spiritual Songs (1707)",
        'tcp-tate-brady': "Tate and Brady's New Version (1696)", 'ccel-scottish-psalter': 'the Scottish Psalter (1650)',
        'ccel-olney': 'the Olney Hymns (1779)', 'kjv-overlap': 'computed',
    };
    // Titles that only number an item ("Psalm 23, part 3", "Olney Hymns 1.127"): lead with the first line
    const NUMBER_TITLE = /^(psalm \d+(,? (part|c\.?m\.?|l\.?m\.?|s\.?m\.?).*)?|olney hymns [\d.]+|paraphrase \d+|hymn [\d.]+)$/i;
    const decode = (s) => String(s ?? '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"');

    function refLabel(l) {
        const book = l.book === 'Psalms' ? 'Psalm' : l.book;
        if (l.verse_start == null) return `${book} ${l.chapter}`;
        return l.verse_end && l.verse_end > l.verse_start ? `${book} ${l.chapter}:${l.verse_start}–${l.verse_end}` : `${book} ${l.chapter}:${l.verse_start}`;
    }

    window.BibleHymns = { refLabel, NUMBER_TITLE };

    window.BibleModules.hymns = {
        studyHymns: { key: null, status: 'idle', passage: [], chapter: [], sources: {} },
        hymnSheet: null,   // { id, status, data, error }

        async studyLoadHymns() {
            const { book, chapter, vs, ve } = this.study;
            const ref = `${book} ${chapter}:${vs}${ve > vs ? '-' + ve : ''}`;
            if (this.studyHymns.key === ref && this.studyHymns.status === 'ready') return;
            Object.assign(this.studyHymns, { key: ref, status: 'loading', passage: [], chapter: [] });
            try {
                const d = await this.studyFetch(`/api/hymns/for-passage?ref=${encodeURIComponent(ref)}&limit=60`);
                if (this.studyHymns.key !== ref) return;
                const hymns = d.hymns || [];
                Object.assign(this.studyHymns, {
                    status: 'ready', sources: d.sources || {},
                    passage: hymns.filter(h => h.match === 'passage'), chapter: hymns.filter(h => h.match !== 'passage'),
                });
            } catch {
                // Offline or no index: no pane, never an error box (hymns are an extra)
                if (this.studyHymns.key === ref) this.studyHymns.status = 'none';
            }
            if (this.study.active !== 'hymns') return;
            // Opened at the hymns (a link, Back): place the track once the pane exists;
            // no hymns here: the first pane instead
            if (this.studyHymnsShown()) this.$nextTick(() => this.studyScrollToSource('hymns', false));
            else this.studySelect(this.studyPaneOrder()[0], { scroll: true });
        },
        studyHymnsShown() {
            return this.studyHymns.status === 'ready' && (this.studyHymns.passage.length + this.studyHymns.chapter.length) > 0;
        },
        studyHymnCount() { return this.studyHymns.passage.length; },
        studyHymnsLabel() {
            const n = this.studyHymns.passage.length;
            const c = this.studyHymns.chapter.length;
            if (n) return `Hymns on ${this.studyRefLabel()}: ${n}`;
            return `Hymns on other verses of ${this.study.book} ${this.study.chapter}: ${c}`;
        },

        // What a hymn card shows
        hymnHead(h) {
            const title = decode(h.title);
            const first = h.first_line ? decode(h.first_line) : null;
            if (first && NUMBER_TITLE.test(title.trim())) return { head: first, sub: title, firstShown: true };
            return { head: title, sub: null, firstShown: false };
        },
        hymnFirstLine(h) {
            const hd = this.hymnHead(h);
            if (hd.firstShown || !h.first_line) return null;
            const first = decode(h.first_line);
            return first.toLowerCase().replace(/[^a-z]/g, '') === decode(h.title).toLowerCase().replace(/[^a-z]/g, '') ? null : first;
        },
        hymnWho(h) {
            const parts = [];
            if (h.author) parts.push(decode(h.author).replace(/(\d)-(\d)/g, '$1–$2'));
            if (h.translator) parts.push(`tr. ${decode(h.translator).replace(/(\d)-(\d)/g, '$1–$2')}`);
            let who = parts.join('; ');
            if (h.words_year && !who.includes(String(h.words_year))) who += who ? `, ${h.words_year}` : String(h.words_year);
            return who;
        },
        hymnTune(h) {
            const tune = h.tune ? decode(h.tune).replace(/`/g, '’') : null;
            const meter = h.meter ? decode(h.meter) : null;
            if (tune && meter) return `Tune: ${tune} (${meter})`;
            if (tune) return `Tune: ${tune}`;
            if (meter) return `Meter: ${meter}`;
            return '';
        },
        // Why it is linked, in the source's terms. kind: quotes | paraphrase | based_on | reference
        hymnWhy(l) {
            const ref = refLabel(l);
            const src = SOURCE_SHORT[l.source] || l.source;
            switch (l.kind) {
                case 'quotes': return { text: `Shares a run of words with ${ref} in the KJV`, computed: true, evidence: l.evidence };
                case 'paraphrase':
                    if (l.source === 'openhymnal-credit') return { text: `Its credit line names ${ref}: “${decode(l.evidence || l.as_written)}”` };
                    return { text: `A metrical version of ${ref}, from ${src}` };
                case 'based_on': return { text: `${ref} is printed with it in ${src}` };
                default: return { text: `Listed under ${ref} in ${src}'s Scripture index` };
            }
        },
        hymnLinkOf(h) { return h.links?.[0] || null; },
        hymnComputedLink(h) {
            const best = this.hymnLinkOf(h);
            return best?.kind === 'quotes' ? null : (h.links || []).find(l => l.kind === 'quotes') || null;
        },
        hymnSourcesShown() {
            const keys = new Set();
            for (const h of [...this.studyHymns.passage, ...this.studyHymns.chapter]) {
                (h.sources_for_text || [h.source]).forEach(k => keys.add(k));
                (h.links || []).forEach(l => keys.add(l.source));
            }
            return [...keys].map(k => ({ key: k, ...(this.studyHymns.sources[k] || {}) })).filter(s => s.name);
        },

        // ---------- one hymn ----------
        async hymnOpen(h) {
            const id = h.id;
            this.hymnSheet = { id, status: 'loading', data: { ...h, passages: null }, error: null };
            this.$nextTick(() => document.getElementById('study-hymn')?.showModal());
            try {
                const d = await this.studyFetch(`/api/hymns/${encodeURIComponent(id)}`);
                if (this.hymnSheet?.id !== id) return;
                Object.assign(this.hymnSheet, { status: 'ready', data: d });
            } catch (err) {
                if (this.hymnSheet?.id !== id) return;
                Object.assign(this.hymnSheet, { status: 'error', error: err.offline || !navigator.onLine ? 'This hymn needs a connection.' : "Couldn't load this hymn. Try again." });
            }
        },
        hymnClose() {
            document.getElementById('study-hymn')?.close();
            this.hymnSheet = null;
        },
        // Every passage once, with all the reasons it is linked
        hymnPassages() {
            const ps = this.hymnSheet?.data?.passages;
            if (!ps) return [];
            const byRef = new Map();
            for (const l of ps) {
                const key = refLabel(l);
                if (!byRef.has(key)) byRef.set(key, { label: key, link: l, whys: [] });
                const why = this.hymnWhy(l);
                const entry = byRef.get(key);
                if (!entry.whys.some(w => w.text === why.text)) entry.whys.push(why);
            }
            return [...byRef.values()];
        },
        hymnStudyPassage(p) {
            const l = p.link;
            const ref = l.verse_start == null ? `${l.book} ${l.chapter}`
                : `${l.book} ${l.chapter}:${l.verse_start}${l.verse_end > l.verse_start ? '-' + l.verse_end : ''}`;
            this.hymnClose();
            this.openStudy(ref, { history: 'push' });
        },
        hymnSheetSources() {
            const d = this.hymnSheet?.data;
            if (!d?.sources) return [];
            const keys = new Set([d.source, ...(d.passages || []).map(p => p.source), ...(d.other_settings || []).map(o => o.source)]);
            return [...keys].filter(k => d.sources[k]).map(k => ({ key: k, ...d.sources[k] }));
        },
        hymnSourceShort(k) { return SOURCE_SHORT[k] || k; },
        hymnDecode(s) { return decode(s); },
    };
})();
