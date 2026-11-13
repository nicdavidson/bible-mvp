// bibleApp feature module: nav — the one way the reader moves between passages.
// Merged via Object.assign in app.js. Markup: the header title button, the passage
// picker (<dialog id="passage-picker"> plus the inline copy on Home), the return chip.
//
// Every passage change goes through navigate(target, { kind, source }):
//   target  'rom 8:28' (any sloppy form) | { plan: { id, day } } | { home: true }
//   kind    'read'  reading on: previous/next, picker, Recent, bookmark. Clears the return chip.
//           'jump'  cross-reference, search hit, topic, note link, word occurrence,
//                   commentary link, path to Christ. Shows "Back to <where you were>".
//           'stay'  same place, new rendering (translation switch). Keeps the chip.
//   source  'user'    pushes one history entry
//           'pop'     browser Back/Forward: never touches history
//           'init'    first load / reload: replaces the entry, restores its chip
//           'replace' same entry, new content (translation switch)
// History entries carry { nav: 1, idx, ref | plan | home, ret, scroll }. idx is the
// entry's position in this tab's stack, so the chip can return with history.go() and
// Back always agrees with it. The study view (modules/study.js) pushes its own entries
// through navPushState()/navReplaceState() so the numbering stays right.
window.BibleModules = window.BibleModules || {};
(() => {
    const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const finePointer = () => window.matchMedia('(pointer: fine)').matches;

    // ---------- references (pure; window.BibleRef for tests) ----------
    const ORDINAL = { i: '1', ii: '2', iii: '3', first: '1', second: '2', third: '3' };
    let NOSPACE = null;   // "1john" -> "1 John", built from the app's BOOK_ABBREVS table

    // A book name or abbreviation -> { book } or { candidates: [...] } (ambiguous) or {}.
    function lookupBook(raw) {
        let s = String(raw || '').toLowerCase().replace(/\./g, ' ').replace(/\s+/g, ' ').trim();
        if (!s) return {};
        s = s.replace(/^(iii|ii|i|first|second|third)\s+(?=[a-z])/, (m, o) => ORDINAL[o] + ' ');
        s = s.replace(/^([123])\s*(?=[a-z])/, '$1 ');
        if (BOOK_NAME_LOOKUP[s]) return { book: BOOK_NAME_LOOKUP[s] };
        if (!NOSPACE) {
            NOSPACE = {};
            for (const [abbr, full] of Object.entries(BOOK_ABBREVS)) NOSPACE[abbr.toLowerCase().replace(/\s+/g, '')] = full;
        }
        const flat = s.replace(/\s+/g, '');
        if (NOSPACE[flat]) return { book: NOSPACE[flat] };
        // Unambiguous beginning of a book name: "matth", "revel", "1 cori"
        const hits = BIBLE_BOOKS.filter(b => b.toLowerCase().replace(/\s+/g, '').startsWith(flat));
        if (hits.length === 1) return { book: hits[0] };
        return hits.length ? { candidates: hits } : {};
    }

    // Any reasonable way of writing a reference -> canonical parts, or { error }.
    //   "rom 8:28", "Rom. 8.28", "jn3:16", "john 3 16", "1jn 4:8", "ps 23", "Jude 5",
    //   "Genesis 1-3" (a chapter range opens its first chapter), "John 3:18-16" (reversed)
    // A bare book ("psalms") returns { book } with no chapter.
    function parseRef(input) {
        const s = String(input || '').replace(/\s+/g, ' ').trim();
        if (!s) return { error: 'Type a book and chapter, like John 3 or Romans 8:28.' };
        const m = s.match(/^((?:[123]|i{1,3})?\s*[^\d]+?)\.?\s*(\d+)?\s*(?:([:.\s])\s*(\d+))?(?:\s*[-–—]\s*(\d+))?\s*$/i);
        if (!m) return { error: `"${s}" doesn't look like a Bible reference. Try John 3 or Romans 8:28.` };
        const found = lookupBook(m[1]);
        if (!found.book) {
            return found.candidates
                ? { error: `Which book? ${found.candidates.join(', ')}.`, candidates: found.candidates }
                : { error: `There's no book called "${m[1].trim()}".` };
        }
        const book = found.book;
        const max = BOOK_CHAPTERS[book] || 1;
        if (!m[2]) return { book };
        let chapter = parseInt(m[2], 10);
        let vs = m[4] ? parseInt(m[4], 10) : null;
        let ve = vs != null && m[5] ? parseInt(m[5], 10) : vs;
        // "Jude 5" means verse 5 of Jude's one chapter
        if (max === 1 && vs == null && chapter > 1) { vs = chapter; ve = m[5] ? parseInt(m[5], 10) : vs; chapter = 1; }
        if (chapter < 1 || chapter > max) {
            return { error: `${book} has ${max} chapter${max === 1 ? '' : 's'}.`, book };
        }
        if (vs != null && vs < 1) vs = 1;
        if (vs != null && ve < vs) [vs, ve] = [ve, vs];
        return { book, chapter, vs, ve };
    }

    function formatRef({ book, chapter, vs, ve }) {
        if (!vs) return `${book} ${chapter}`;
        return ve && ve > vs ? `${book} ${chapter}:${vs}-${ve}` : `${book} ${chapter}:${vs}`;
    }

    function refPath({ book, chapter, vs, ve }) {
        const slug = book.replace(/\s+/g, '-');
        if (!vs) return `/${slug}/${chapter}`;
        return ve && ve > vs ? `/${slug}/${chapter}/${vs}-${ve}` : `/${slug}/${chapter}/${vs}`;
    }

    // The location in the address bar: { ref } | { plan } | { home } | null (unknown path)
    function locationFromURL() {
        const path = window.location.pathname;
        const plan = path.match(/^\/plan\/([^/]+)\/(\d+)$/);
        if (plan) return { plan: { id: decodeURIComponent(plan[1]), day: parseInt(plan[2], 10) } };
        const p = path.match(/^\/([^/]+)\/(\d+)(?:\/(\d+)(?:-(\d+))?)?$/);
        if (p) {
            const book = decodeURIComponent(p[1]).replace(/-/g, ' ');
            return { ref: p[3] ? `${book} ${p[2]}:${p[3]}${p[4] ? '-' + p[4] : ''}` : `${book} ${p[2]}` };
        }
        const legacy = new URLSearchParams(window.location.search).get('ref');
        if (legacy) return { ref: legacy };
        if (path === '/') return { home: true };
        return null;
    }

    window.BibleRef = { parse: parseRef, format: formatRef, path: refPath, lookupBook };

    window.BibleModules.nav = {
        navReturn: null,      // { ref | plan | study, label, idx, search? } while a jump can be undone
        navBusy: false,       // a navigation is between its start and its history/scroll update
        _navIdx: 0,
        picker: { open: false, step: 'books', book: null, tab: 'books', query: '' },

        // ---------- startup ----------
        async navInit() {
            if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
            this.migrateReadingHistory();
            const st = history.state;
            if (st?.nav) this._navIdx = st.idx || 0;
            const loc = locationFromURL();
            const studySource = new URLSearchParams(window.location.search).get('study');
            let ok = false;
            if (await this.wsInitFromURL()) ok = true;          // /word/G26 (modules/wordstudy.js)
            else if (loc && !loc.home) {
                ok = await this.navigate(loc.plan ? { plan: loc.plan } : loc.ref, { source: 'init', state: st });
                if (ok && loc.ref && studySource !== null) {
                    this.openStudy(loc.ref, { source: studySource, history: 'replace' });
                }
            }
            // A bad link (unknown book, missing plan) shows Home with the reason
            if (!ok && (!loc || !loc.ref)) await this.navigate({ home: true }, { source: 'init' });

            window.addEventListener('popstate', (e) => this.navOnPop(e));
            this.$watch('translation', () => this.navReloadHere());
            // The entry follows the selection (a range too: /John/3/16-18), never mid-navigation
            this.$watch('highlightedVerses', () => { if (!this.navBusy && !this.loading) this.updateURL(); });
            this.pickerInitDialog();
        },

        navOnPop(e) {
            const st = e.state;
            const wordWasOpen = this.ws?.open;
            if (this.wsHandlePop(e)) {                     // a word study entry: wordstudy.js showed it
                if (st?.nav) this._navIdx = st.idx || 0;
                if (this.study?.open) this.studyHide();
                return;
            }
            const closedStudyHere = this.studyHandlePop(e);
            if (st?.nav) this._navIdx = st.idx || 0;
            if (st?.study) return;                       // a study view entry: study.js showed it
            if (closedStudyHere) {                       // study closed onto the chapter underneath
                this.navReturn = st?.ret || null;
                return;
            }
            const loc = locationFromURL();
            if (!loc) return;
            // The word study closed onto the chapter already underneath: nothing to reload
            if (wordWasOpen && loc.ref) {
                const r = parseRef(loc.ref);
                if (r.book === this.currentBook && r.chapter === this.currentChapter) { this.navReturn = st?.ret || null; return; }
            }
            if (wordWasOpen && loc.home && !this.currentBook && !this.combinedPlanReading) { this.navReturn = st?.ret || null; return; }
            this.navigate(loc.plan ? { plan: loc.plan } : loc.home ? loc : loc.ref, { source: 'pop', state: st });
        },

        // Push/replace with this tab's entry numbering (also used by the study view).
        // States are plain JSON: Alpine's reactive proxies (navReturn) can't be cloned.
        navPushState(state, url) {
            this._navIdx += 1;
            history.pushState(JSON.parse(JSON.stringify({ ...state, idx: this._navIdx })), '', url);
        },
        navReplaceState(state, url) {
            history.replaceState(JSON.parse(JSON.stringify({ ...state, idx: this._navIdx })), '', url);
        },

        // ---------- the one entry point ----------
        async navigate(target, { kind = 'read', source = 'user', state = null, section = null, fromSearch = false } = {}) {
            // Resolve the target to a canonical location before anything changes
            let loc;
            if (typeof target === 'string') {
                const r = parseRef(target);
                if (r.error || !r.chapter) {
                    const msg = r.error || `Pick a chapter of ${r.book}.`;
                    if (source === 'user' && this.verses.length) this.showToast(msg, 'error');
                    else { this.error = msg; this.verses = []; }
                    return false;
                }
                loc = { r, ref: formatRef(r) };
            } else if (target?.ref) {
                return this.navigate(target.ref, { kind, source, state, section, fromSearch });
            } else {
                loc = target || { home: true };
            }

            this._navPending = (this._navPending || 0) + 1;
            this.navBusy = true;
            try {
                return await this._navigate(loc, { kind, source, state, section, fromSearch });
            } finally {
                this._navPending -= 1;
                this.navBusy = this._navPending > 0;
            }
        },

        async _navigate(loc, { kind, source, state, section, fromSearch }) {
            const from = source === 'user' && kind === 'jump' ? this.navHere() : null;
            const keepScroll = kind === 'stay' ? this._navScroller()?.scrollTop : null;
            if (source === 'user') this._navSaveScroll();
            this._navCloseOverlays(kind);

            let ok;
            if (loc.home) {
                this._navShowHome();
                ok = true;
            } else if (loc.plan) {
                ok = await this._loadPlanDay(loc.plan);
            } else {
                this._navLeavePlan();
                ok = await this.loadPassage(loc.r, { keepOnError: source === 'user' && this.verses.length > 0 });
            }
            if (ok !== true) return false;

            // The way back: a jump remembers where reading was (the first place, through
            // chained jumps); reading on forgets it; Back/Forward restore the entry's own.
            if (source === 'pop' || source === 'init') this.navReturn = state?.ret || null;
            else if (kind === 'jump') {
                const base = this.navReturn || from;
                this.navReturn = base && { ...base, search: fromSearch };   // "Results" goes back to the search
            }
            else if (kind === 'read') this.navReturn = null;

            const entry = { nav: 1, ...this._navLocation(), ret: this.navReturn };
            if (source === 'user') this.navPushState(entry, this._navPath());
            else if (source !== 'pop' || !state?.nav) this.navReplaceState({ ...state, ...entry }, this._navPath());

            if (loc.r && source !== 'pop') this.addToHistory(this.currentReference, this.translation);
            this._navPlaceScroll(source === 'pop' || source === 'init' ? state?.scroll : keepScroll, section);
            return true;
        },

        // Where the reader is now, as a chip target. Null on Home (nothing to return to).
        navHere() {
            const idx = this._navIdx;
            if (this.ws?.open && this.ws.strong) {
                const name = this.ws.data?.lemma?.transliteration || this.ws.strong;
                return { word: this.ws.strong, homograph: this.ws.homograph, label: `the word study of ${name}`, idx };
            }
            if (this.study?.open && this.study.book) {
                const what = { 'cross-references': 'cross-references', notes: 'your notes', hymns: 'hymns' }[this.study.active] || 'commentary';
                return { study: true, ref: this.studyRefLabel().replace('–', '-'), label: `${what} on ${this.studyRefLabel()}`, idx };
            }
            if (this.combinedPlanReading && this.currentPlan) {
                return { plan: { id: this.currentPlan.id, day: this.planDay }, label: `Day ${this.planDay} reading`, idx };
            }
            if (!this.currentBook || !this.currentChapter) return null;
            const ref = this.studySelectionRef();
            return { ref, label: ref, idx };
        },

        // Tap on the chip: back to where reading was, the same way browser Back would.
        navGoBack() {
            const ret = this.navReturn;
            if (!ret) return;
            const here = history.state?.nav ? history.state.idx : null;
            if (ret.idx != null && here != null && ret.idx < here) {
                history.go(ret.idx - here);
                return;
            }
            // History was cut (new tab from a shared link): go there as reading
            if (ret.word) this.openWordStudy(ret.word, { homograph: ret.homograph || null });
            else if (ret.study) this.navigate(ret.ref, { kind: 'read' }).then(ok => ok && this.openStudy(ret.ref));
            else this.navigate(ret.plan ? { plan: ret.plan } : ret.ref, { kind: 'read' });
        },

        navDismissReturn() {
            this.navReturn = null;
            if (history.state?.nav) this.navReplaceState({ ...history.state, ret: null }, location.pathname + location.search);
            document.querySelector('.panel-text .panel-body')?.focus({ preventScroll: true });
        },

        navReopenSearch() {
            this.showSearch = true;
            this.$nextTick(() => this.$refs.searchInput?.focus());
        },

        // ---------- reading on ----------
        _adjacentChapter(dir) {
            if (!this.currentBook) return null;
            const i = BIBLE_BOOKS.indexOf(this.currentBook);
            const ch = this.currentChapter + dir;
            if (ch >= 1 && ch <= (BOOK_CHAPTERS[this.currentBook] || 1)) return `${this.currentBook} ${ch}`;
            const book = BIBLE_BOOKS[i + dir];
            if (!book) return null;
            return dir > 0 ? `${book} 1` : `${book} ${BOOK_CHAPTERS[book] || 1}`;
        },
        prevLabel() { return this.combinedPlanReading ? `Day ${this.planDay - 1}` : this._adjacentChapter(-1); },
        nextLabel() { return this.combinedPlanReading ? `Day ${this.planDay + 1}` : this._adjacentChapter(1); },

        // In plan reading these step through the plan's days (P0-5).
        previousChapter() {
            if (this.loading) return;
            if (this.combinedPlanReading) return this.planStep(-1);
            const ref = this._adjacentChapter(-1);
            if (ref) this.navigate(ref, { kind: 'read' });
        },
        nextChapter() {
            if (this.loading) return;
            if (this.combinedPlanReading) return this.planStep(1);
            const ref = this._adjacentChapter(1);
            if (ref) this.navigate(ref, { kind: 'read' });
        },

        goHome() {
            this.showSideMenu = false;
            this.navigate({ home: true });
        },

        // Translation changed: the same place in the new text, no new history entry
        navReloadHere() {
            if (this.combinedPlanReading && this.currentPlan) {
                this.navigate({ plan: { id: this.currentPlan.id, day: this.planDay } }, { kind: 'stay', source: 'replace' });
            } else if (this.currentBook && this.currentChapter) {
                this.navigate(this.studySelectionRef(), { kind: 'stay', source: 'replace' });
            }
        },

        // The passage named by the address bar ("John 3:16"), or null
        parsePathReference() {
            return locationFromURL()?.ref || null;
        },

        // Selecting verses inside the chapter rewrites the current entry (no new entry).
        // While the study view is open it owns the address bar (modules/study.js).
        updateURL() {
            if (this.study?.open) return;
            if (!this.combinedPlanReading && !this.currentBook) return;
            this.navReplaceState({ ...(history.state?.study ? {} : history.state), nav: 1, ...this._navLocation(), ret: this.navReturn }, this._navPath());
        },

        // ---------- internals ----------
        _navLocation() {
            if (this.combinedPlanReading && this.currentPlan) return { plan: { id: this.currentPlan.id, day: this.planDay } };
            if (!this.currentBook) return { home: true };
            return { ref: this.studySelectionRef() };
        },
        _navPath() {
            if (this.combinedPlanReading && this.currentPlan) return `/plan/${encodeURIComponent(this.currentPlan.id)}/${this.planDay}`;
            if (!this.currentBook) return '/';
            const vv = [...this.highlightedVerses].sort((a, b) => a - b);
            return refPath({ book: this.currentBook, chapter: this.currentChapter, vs: vv[0], ve: vv[vv.length - 1] });
        },
        // The reading pane scrolls on phones; the window does on wide screens
        _navScroller() {
            const pane = document.querySelector('.panel-text .panel-body');
            return pane && pane.scrollHeight > pane.clientHeight + 1 ? pane : document.scrollingElement;
        },
        _navSaveScroll() {
            if (!history.state?.nav) return;
            const el = this._navScroller();
            history.replaceState({ ...history.state, scroll: el ? Math.round(el.scrollTop) : 0 }, '');
        },
        _navPlaceScroll(saved, section) {
            // The header shows where you are: bring it back, and don't let this scroll hide it
            this._navScrolledAt = Date.now();
            document.body.classList.remove('reading-immersed');
            this.$nextTick(() => requestAnimationFrame(() => {
                this._navScrolledAt = Date.now();
                const el = this._navScroller();
                if (!el) return;
                if (saved != null) { el.scrollTop = saved; return; }
                const target = section
                    ? document.querySelector(`.combined-section-header.section-${CSS.escape(section)}`)
                    : this.highlightedVerses.length ? document.getElementById(`verse-${this.highlightedVerses[0]}`) : null;
                if (target) target.scrollIntoView({ block: section ? 'start' : 'center', behavior: 'auto' });
                else el.scrollTop = 0;
                // Window may scroll too on phones (header auto-hide): start at the top
                if (el !== document.scrollingElement && !target) window.scrollTo(0, 0);
            }));
        },
        _navCloseOverlays(kind) {
            this.showSearch = false;
            this.showSideMenu = false;
            this.showPathToChrist = false;
            this.showMemoryTool = false;
            this.showShareJesus = false;
            this.showReadingPlan = false;
            this.selectedWord = null;
            this.actionMore = false;
            this.closePicker();
            if (this.study?.open) this.studyHide();   // "Read the chapter" from the study view
            if (this.ws?.open) this.wsHide();         // "Read in context" from a word study
            // After a jump on a phone, fold the sheet so the verse and the chip both show (P1-10)
            if (kind === 'jump' && window.innerWidth <= 600) {
                this.resourcesPanelExpanded = false;
                this.sheetSnap = 'collapsed';
                this.sheetDragStyle = '';
            }
        },
        _navLeavePlan() {
            if (!this.combinedPlanReading) return;
            Object.assign(this, {
                combinedPlanReading: false, planReadingSections: [], planReadingChapters: [],
                combinedCrossRefs: [], combinedNotes: [],
            });
        },
        _navShowHome() {
            this._navLeavePlan();
            this._loadGeneration++;   // drop any in-flight passage load
            if (this.ttsPlaying) this.ttsStop();
            this.currentView = 'reader';
            Object.assign(this, {
                verses: [], currentBook: null, currentChapter: null, currentReference: '',
                highlightedVerses: [], crossRefs: [], verseTopics: [], error: null,
                loading: false, selectionContext: null,
            });
            this.picker.step = 'books';
            this.picker.book = null;
            this.picker.query = '';
        },

        // ---------- Recent ----------
        // Recent is one entry per chapter, newest first, always canonical ("Romans 8:28",
        // never "rom 8:28"). Older saves are cleaned up once on load; the format is unchanged.
        migrateReadingHistory() {
            const seen = new Set();
            const clean = [];
            for (const h of this.readingHistory || []) {
                const r = parseRef(h?.reference);
                if (r.error || !r.chapter) continue;
                const key = `${r.book} ${r.chapter}`;
                if (seen.has(key)) continue;
                seen.add(key);
                clean.push({ ...h, reference: formatRef(r) });
            }
            if (JSON.stringify(clean) !== JSON.stringify(this.readingHistory)) {
                this.readingHistory = clean;
                try { localStorage.setItem('readingHistory', JSON.stringify(clean)); } catch { /* quota */ }
            }
        },

        // ---------- the picker ----------
        navTitle() {
            if (this.combinedPlanReading && this.currentPlan) return `Day ${this.planDay}`;
            if (this.currentBook && this.currentChapter) return `${this.currentBook} ${this.currentChapter}`;
            return 'Choose a passage';
        },

        pickerInitDialog() {
            const dlg = document.getElementById('passage-picker');
            if (!dlg) return;
            dlg.addEventListener('close', () => { this.picker.open = false; });
            // Tap outside to close where closedby="any" isn't supported (Safari)
            if (!('closedBy' in HTMLDialogElement.prototype)) {
                dlg.addEventListener('click', (e) => {
                    if (e.target !== dlg) return;
                    const r = dlg.getBoundingClientRect();
                    if (e.clientY < r.top || e.clientY > r.bottom || e.clientX < r.left || e.clientX > r.right) dlg.close();
                });
            }
        },

        // The header button opens at the books (John 3 -> Psalm 23 is three taps); the
        // passage title opens at the current book's chapters (the next chapter is two).
        // The current book and chapter are marked either way.
        openPicker({ step = 'books', focusInput = false } = {}) {
            const dlg = document.getElementById('passage-picker');
            if (!dlg) return;
            const atBook = step === 'chapters' && this.currentBook;
            Object.assign(this.picker, {
                open: true, query: '', tab: 'books',
                step: atBook ? 'chapters' : 'books', book: atBook ? this.currentBook : null,
            });
            if (!dlg.open) dlg.showModal();
            this.$nextTick(() => {
                const scope = dlg;
                if (focusInput || finePointer()) scope.querySelector('.picker-input')?.focus();
                else scope.querySelector('.picker-chapter.is-current, .picker-book.is-current, .picker-close')?.focus();
                scope.querySelector('.picker-chapter.is-current')?.scrollIntoView({ block: 'center' });
            });
        },
        closePicker() {
            const dlg = document.getElementById('passage-picker');
            if (dlg?.open) dlg.close();
            this.picker.open = false;
        },

        pickerBooks(testament) {
            const list = testament === 'ot' ? OT_BOOKS : NT_BOOKS;
            // Filter by the book part of what's typed: "rom 8:28" -> "rom", "1 cor" stays
            const q = (this.picker.query.match(/^\s*((?:[123]\s*)?[^\d]*)/)?.[1] || '').trim();
            if (!q) return list;
            const flat = q.toLowerCase().replace(/[.\s]+/g, '');
            const hit = lookupBook(q).book;
            return list.filter(b => b === hit || b.toLowerCase().replace(/\s+/g, '').startsWith(flat)
                || b.toLowerCase().split(' ').some(w => w.startsWith(flat)));
        },
        // What Enter would do with the typed text, for the "Go to ..." row
        pickerTyped() {
            const q = this.picker.query.trim();
            if (!q) return null;
            const r = parseRef(q);
            if (r.chapter) return { ref: formatRef(r) };
            if (r.book && !r.error) return { book: r.book };
            return /\d/.test(q) ? { error: r.error } : null;   // still typing a book name
        },
        pickerSubmit(event) {
            const t = this.pickerTyped();
            if (!t) {
                const only = [...this.pickerBooks('ot'), ...this.pickerBooks('nt')];
                if (only.length === 1) this.pickBook(only[0], event);
                return;
            }
            if (t.ref) this._pickerGo(t.ref);
            else if (t.book) this.pickBook(t.book, event);
        },
        pickBook(book, event) {
            if ((BOOK_CHAPTERS[book] || 1) === 1) { this._pickerGo(`${book} 1`); return; }
            this.picker.step = 'chapters';
            this.picker.book = book;
            this.picker.query = '';
            const root = event?.target?.closest('[data-picker-root]');
            this.$nextTick(() => {
                const cur = root?.querySelector('.picker-chapter.is-current');
                (cur || root?.querySelector('.picker-chapter'))?.focus({ preventScroll: true });
                cur?.scrollIntoView({ block: 'center' });
                if (!cur) root?.querySelector('.picker-chapters-head')?.scrollIntoView({ block: 'nearest' });
            });
        },
        pickerAllBooks(event) {
            const book = this.picker.book;
            this.picker.step = 'books';
            this.picker.book = null;
            const root = event?.target?.closest('[data-picker-root]');
            this.$nextTick(() => {
                const btn = root?.querySelector(`.picker-book[data-book="${CSS.escape(book || '')}"]`);
                btn?.focus({ preventScroll: true });
                btn?.scrollIntoView({ block: 'center' });
            });
        },
        pickChapter(ch) { this._pickerGo(`${this.picker.book} ${ch}`); },
        pickerChapters() { return this.getChaptersArray(this.picker.book); },
        _pickerGo(ref) {
            this.closePicker();
            this.navigate(ref, { kind: 'read' });
        },
        pickRecent(item) { this._pickerGo(item.reference); },
    };
})();
