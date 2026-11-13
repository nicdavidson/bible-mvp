// The walkthrough: dims the page, rings one real control at a time and explains it in a
// small dialog (Back / Next / Skip, "3 of 8"). An ES module, imported only when it runs:
// app.js tourArm() (once per device, on a plain first load) and tourStart() (Settings >
// General > Show the walkthrough). Styles: css/tour.css, loaded from here.
//
// Some controls exist only after the reader does something (the action bar, the study
// view, the word panel). A step names what it needs ('selection', 'study', 'word'); the
// tour sets that up through the app's own functions, waits a bounded time for the
// control, and takes down what it set up as soon as a step doesn't need it, and always
// when the tour ends (Done, Skip, Escape, Back button), so the reader ends where they
// started. A control that doesn't turn up drops its step. The dim layer is part of the
// tour's own <dialog>, so it can never outlive the tour.

const DONE_KEY = 'tourDone';                        // app.js tourArm() reads it
const VERSION = new URL(import.meta.url).search;    // '?v=<deploy>', as the service worker caches it
const WAIT_MS = 4000;                               // longest wait for a staged control
const PAD = 6;                                      // ring around the control
const GAP = 12;                                     // control to caption
const EDGE = 12;                                    // caption to screen edge

const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (sel) => document.querySelector(sel);

function shown(el) {
    if (!el || !el.isConnected || !el.getClientRects().length) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
}

// Resolves with test()'s first truthy value, or null on timeout or once alive() is false.
function waitFor(test, ms, alive) {
    return new Promise((resolve) => {
        const t0 = performance.now();
        const tick = () => {
            if (!alive()) return resolve(null);
            let v = null;
            try { v = test(); } catch (e) { v = null; }
            if (v) return resolve(v);
            if (performance.now() - t0 > ms) return resolve(null);
            setTimeout(tick, 50);
        };
        tick();
    });
}

function loadStyles() {
    if ($('link[data-tour-css]')) return Promise.resolve(true);
    return new Promise((resolve) => {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `/static/css/tour.css${VERSION}`;
        link.dataset.tourCss = '';
        link.onload = () => resolve(true);
        link.onerror = () => { link.remove(); resolve(false); };
        document.head.append(link);
        setTimeout(() => resolve(!!link.sheet), 5000);
    });
}

function setDone() {
    try { localStorage.setItem(DONE_KEY, '1'); } catch (e) { /* storage gone: nothing to keep */ }
}

const lang = (app) => (app.otBooks?.includes(app.currentBook) ? 'Hebrew' : 'Greek');

// chapter: needs verses on screen (left out on Home). optional: no control is fine, the
// caption is centred instead.
const STEPS = [
    {
        id: 'picker', title: 'Choose a passage',
        text: 'Tap here to pick a book and chapter, or to type a reference like John 3:16.',
        target: () => $('.header .nav-title'),
    },
    {
        id: 'select', chapter: true, needs: ['selection'], title: 'Select verses',
        text: 'Tap a verse to select it. Tap a second verse to select every verse in between.',
        target: () => $('.verses .verse-box.verse-highlighted'),
    },
    {
        id: 'study', chapter: true, needs: ['selection'], title: 'Study',
        text: 'Study opens the commentaries on the verses you selected.',
        target: () => $('.verse-action-bar .action-bar-study'),
    },
    {
        id: 'sources', chapter: true, needs: ['selection', 'study'], title: 'Commentaries',
        text: 'Swipe left or right to move between commentaries, or tap a name at the bottom.',
        target: () => $('#study-view .study-chips'),
    },
    {
        id: 'tools', chapter: true, needs: ['selection', 'study'], title: 'Cross-references and notes',
        text: () => (shown($('#study-view .study-tool[data-slug="hymns"]'))
            ? 'These open the cross-references, hymns and your own notes for the verses.'
            : 'These open the cross-references and your own notes for the verses. Hymns appear here when a hymn uses the passage.'),
        target: () => $('#study-view .study-tools'),
    },
    {
        id: 'word', chapter: true, needs: ['selection', 'word'], title: 'Hebrew and Greek',
        text: (app) => `In a selected verse, tap a word to see the ${lang(app)} behind it. “Study this word” opens the full word study.`,
        target: () => $('.panel-word'),
    },
    {
        id: 'search', title: 'Search',
        text: 'Search for words or a reference. Or describe an idea in your own words to find verses close in meaning.',
        target: () => $('.header .header-search'),
    },
    {
        id: 'back', optional: true, title: 'Finding your way back',
        text: 'When you follow a link to another passage, a “Back to …” button appears. Tap it to return to where you were.',
        target: () => $('.return-chip'),
    },
];

let running = null;

export async function startTour(app, { auto = false } = {}) {
    if (running) return;
    running = true;
    try {
        if (!(await loadStyles())) return;          // no styles (offline, not cached): no tour, flag unset
        if (auto) {
            // Still a plain reader with nothing over it? Otherwise try again on a later load.
            const clear = app.verses.length && !app.loading && !app.combinedPlanReading
                && !app.anyModalOpen() && !app.picker?.open && !app.selectedWord
                && !app.study?.open && !app.ws?.open && !$('dialog[open]');
            if (!clear) return;
        } else {
            // From Settings: let its overlay go first
            await waitFor(() => [...document.querySelectorAll('.modal-overlay')].every((o) => !o.getClientRects().length), 1000, () => true);
        }
        await new Tour(app).run();          // resolves when the tour has ended
    } finally {
        running = null;
    }
}

class Tour {
    constructor(app) {
        this.app = app;
        this.ended = false;
        this.busy = false;
        this.index = -1;
        this.dropped = new Set();
        this.staged = new Set();          // what the tour set up, to take down
        this.target = null;
        this.sig = '';
        this.transition = Promise.resolve();
        this.alive = () => !this.ended;
        this.finished = new Promise((resolve) => { this.resolveFinished = resolve; });
        this.steps = STEPS.filter((s) => !s.chapter || (app.verses.length && app.currentBook && !app.combinedPlanReading));
        this.stagers = this.makeStagers();
    }

    // ---------- the dialog ----------
    build() {
        const dlg = document.createElement('dialog');
        dlg.className = 'tour';
        dlg.setAttribute('aria-labelledby', 'tour-title');
        dlg.setAttribute('aria-describedby', 'tour-text');
        dlg.innerHTML = `
            <div class="tour-spot" aria-hidden="true"></div>
            <div class="tour-card">
                <div class="tour-copy">
                    <p class="tour-count" id="tour-count"></p>
                    <h2 class="tour-title" id="tour-title"></h2>
                    <p class="tour-text" id="tour-text"></p>
                </div>
                <div class="tour-actions">
                    <button type="button" class="tour-skip">Skip</button>
                    <button type="button" class="tour-back">Back</button>
                    <button type="button" class="tour-next">Next</button>
                </div>
            </div>`;
        this.dlg = dlg;
        this.spot = dlg.querySelector('.tour-spot');
        this.card = dlg.querySelector('.tour-card');
        this.nextBtn = dlg.querySelector('.tour-next');
        this.backBtn = dlg.querySelector('.tour-back');
        dlg.querySelector('.tour-skip').addEventListener('click', () => this.end());
        this.backBtn.addEventListener('click', () => this.go(-1));
        this.nextBtn.addEventListener('click', () => {
            if (this.isLast()) this.end();
            else this.go(1);
        });
        // The app's shortcuts (arrows change chapter) must not act under the tour
        dlg.addEventListener('keydown', (e) => {
            e.stopPropagation();
            if (e.key === 'Escape') { e.preventDefault(); this.end(); }
        });
        dlg.addEventListener('cancel', (e) => { e.preventDefault(); this.end(); });   // Esc, Android back
        dlg.addEventListener('close', () => { if (!dlg.open) this.end(); });    // closed by something else
        this.onPop = () => this.end();          // Back/Forward mid-tour: the reader left; let them go
        this.onMove = () => this.layout();
        document.body.append(dlg);
    }

    async run() {
        this.opener = document.activeElement;
        this.build();
        this.card.style.visibility = 'hidden';
        this.dlg.classList.add('is-centered');
        this.under = new Set(document.querySelectorAll('dialog:modal'));
        this.dlg.showModal();
        window.addEventListener('popstate', this.onPop);
        window.addEventListener('resize', this.onMove);
        window.addEventListener('orientationchange', this.onMove);
        window.addEventListener('scroll', this.onMove, { capture: true, passive: true });
        window.visualViewport?.addEventListener('resize', this.onMove);
        const loop = () => {
            if (this.ended) return;
            this.layout(true);
            this.raf = requestAnimationFrame(loop);
        };
        this.raf = requestAnimationFrame(loop);
        this.go(1);
        return this.finished;
    }

    // Staging may open a modal dialog (the study view) over ours: put the tour back on top
    raise() {
        const others = [...document.querySelectorAll('dialog:modal')].filter((d) => d !== this.dlg);
        if (others.some((d) => !this.under.has(d))) {
            const hadFocus = this.dlg.contains(document.activeElement) ? document.activeElement : null;
            this.dlg.close();
            this.dlg.showModal();
            (hadFocus || this.nextBtn).focus({ preventScroll: true });
        }
        this.under = new Set(others);
    }

    isLast() {
        return !this.steps.some((s, i) => i > this.index && !this.dropped.has(s.id));
    }

    // ---------- moving between steps ----------
    async go(dir) {
        if (this.busy || this.ended) return;
        this.busy = true;
        this.card.setAttribute('aria-busy', 'true');
        const done = (async () => {
            let i = this.index + dir;
            while (!this.ended) {
                while (i >= 0 && i < this.steps.length && this.dropped.has(this.steps[i].id)) i += dir;
                if (i < 0 || i >= this.steps.length) break;
                if (await this.show(i)) { this.index = i; return true; }
                this.dropped.add(this.steps[i].id);
            }
            if (this.ended) return false;
            // Nothing further back: stay on the step we were on
            if (dir < 0 && this.index >= 0 && await this.show(this.index)) return true;
            return false;
        })();
        this.transition = done;
        const ok = await done;
        this.busy = false;
        this.card?.removeAttribute('aria-busy');
        if (!ok && !this.ended) this.end();
    }

    async show(i) {
        const step = this.steps[i];
        if (!(await this.reconcile(step.needs || []))) return false;
        if (this.ended) return false;
        let el = step.target();
        if (!shown(el)) {
            el = step.optional ? null : await waitFor(() => { const e = step.target(); return shown(e) && e; }, WAIT_MS, this.alive);
            if (!el && !step.optional) return false;
        }
        if (this.ended) return false;
        if (el?.closest('.header')) document.body.classList.remove('reading-immersed');   // the header slid away while scrolling
        if (el) this.scrollTo(el);
        this.raise();

        const text = typeof step.text === 'function' ? step.text(this.app) : step.text;
        const pos = this.steps.filter((s, k) => k <= i && !this.dropped.has(s.id)).length;
        const total = this.steps.filter((s) => !this.dropped.has(s.id)).length;
        this.dlg.querySelector('.tour-count').textContent = `${pos} of ${total}`;
        this.dlg.querySelector('.tour-title').textContent = step.title;
        this.dlg.querySelector('.tour-text').textContent = text;
        this.index = i;
        this.backBtn.classList.toggle('is-hidden', pos === 1);
        this.backBtn.disabled = pos === 1;
        this.nextBtn.textContent = this.isLast() ? 'Done' : 'Next';
        this.target = el;
        this.sig = '';
        this.layout();
        this.card.style.visibility = '';
        if (!this.card.contains(document.activeElement) || (document.activeElement === this.backBtn && pos === 1)) {
            this.nextBtn.focus({ preventScroll: true });
        }
        // After the first step the dialog has been announced: read later steps as they change
        this.dlg.querySelector('.tour-copy').setAttribute('aria-live', 'polite');
        return true;
    }

    scrollTo(el) {
        const r = el.getBoundingClientRect();
        if (r.top >= 0 && r.bottom <= window.innerHeight && r.left >= 0 && r.right <= window.innerWidth) return;
        el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: reduceMotion() ? 'auto' : 'smooth' });
    }

    // ---------- placing the ring and the caption ----------
    layout(fromLoop = false) {
        if (this.ended || !this.card) return;
        const W = document.documentElement.clientWidth;
        const H = window.innerHeight;
        const el = this.target && shown(this.target) ? this.target : null;
        const t = el?.getBoundingClientRect();
        const sig = t ? `${t.top}|${t.left}|${t.width}|${t.height}|${W}|${H}` : `none|${W}|${H}`;
        if (fromLoop && sig === this.sig) return;
        this.sig = sig;

        const cs = getComputedStyle(this.dlg);
        const top0 = EDGE + (parseFloat(cs.paddingTop) || 0);
        const bottom0 = H - EDGE - (parseFloat(cs.paddingBottom) || 0);
        const cw = Math.min(360, W - 32);
        this.card.style.width = `${cw}px`;
        const ch = this.card.offsetHeight;

        let r = t && {
            top: Math.max(t.top - PAD, 2), bottom: Math.min(t.bottom + PAD, H - 2),
            left: Math.max(t.left - PAD, 2), right: Math.min(t.right + PAD, W - 2),
        };
        if (r && (r.bottom - r.top < 8 || r.right - r.left < 8)) r = null;   // scrolled off screen
        this.dlg.classList.toggle('is-centered', !r);
        if (!r) {
            this.place(Math.max(top0, (H - ch) / 2), (W - cw) / 2);
            return;
        }
        // Below the control if it fits, else above; if neither, the side with more room,
        // and the ring is cut back so the caption never covers what it rings.
        const below = bottom0 - (r.bottom + GAP);
        const above = r.top - GAP - top0;
        let top;
        if (below >= ch) top = r.bottom + GAP;
        else if (above >= ch) top = r.top - GAP - ch;
        else if (below >= above) {
            r.bottom = Math.max(r.top + 24, bottom0 - ch - GAP);
            top = r.bottom + GAP;
        } else {
            r.top = Math.min(r.bottom - 24, top0 + ch + GAP);
            top = r.top - GAP - ch;
        }
        Object.assign(this.spot.style, {
            top: `${r.top}px`, left: `${r.left}px`, width: `${r.right - r.left}px`, height: `${r.bottom - r.top}px`,
        });
        const mid = (r.left + r.right) / 2;
        this.place(top, Math.min(Math.max(mid - cw / 2, 16), W - 16 - cw));
    }

    place(top, left) {
        this.card.style.top = `${Math.round(top)}px`;
        this.card.style.left = `${Math.round(left)}px`;
    }

    // ---------- staging: what a step needs on screen ----------
    makeStagers() {
        const app = this.app;
        const alive = this.alive;
        return {
            selection: {
                has: () => app.highlightedVerses.length > 0,
                // The first verse fully in view, so the reading doesn't move
                async up() {
                    const boxes = [...document.querySelectorAll('.verses .verse-box')];
                    const pane = document.querySelector('.panel-text .panel-body')?.getBoundingClientRect();
                    const top = Math.max(pane?.top ?? 0, 0);
                    const bottom = Math.min(pane?.bottom ?? window.innerHeight, window.innerHeight) - 90;  // above the action bar
                    const box = boxes.find((b) => { const r = b.getBoundingClientRect(); return r.top >= top && r.bottom <= bottom; }) || boxes[0];
                    const n = parseInt(box?.id.replace('verse-', ''), 10);
                    if (!n) return false;
                    await app.selectVerse(n);
                    return !!(await waitFor(() => app.highlightedVerses.includes(n), WAIT_MS, alive));
                },
                async down() { if (app.highlightedVerses.length) app.clearVerseSelection(); },
            },
            study: {
                has: () => !!app.study?.open,
                // No history entry: closing goes straight back to the reader (study.js)
                async up() {
                    app.openStudy(null, { history: 'none' });
                    return !!(await waitFor(() => !app.study.loading && shown($('#study-view .study-chip')), WAIT_MS, alive));
                },
                async down() {
                    if (app.study?.open) app.studyClose();
                    await waitFor(() => !app.study.open, 1500, () => true);
                },
            },
            word: {
                has: () => !!app.selectedWord,
                // The longest word of the first selected verse: likely to have a source word
                async up() {
                    const n = Math.min(...app.highlightedVerses);
                    const words = [...document.querySelectorAll(`#verse-${n} .verse-text .word[data-word]`)];
                    const word = words.sort((a, b) => b.dataset.word.length - a.dataset.word.length)[0];
                    if (!word) return false;
                    this.word = word;
                    await app.handleWordClick({ target: word });
                    return !!(await waitFor(() => shown($('.panel-word .qw, .panel-word .word-hint, .panel-word .word-unsure')), WAIT_MS, alive));
                },
                async down() {
                    const close = $('.panel-word .btn-close');
                    if (app.selectedWord && close) close.click();
                    this.word?.classList.remove('selected');
                    this.word = null;
                },
            },
        };
    }

    async reconcile(needs) {
        const order = ['selection', 'study', 'word'];
        for (const k of [...order].reverse()) {
            if (this.staged.has(k) && !needs.includes(k)) {
                this.staged.delete(k);
                await this.stagers[k].down();
            }
        }
        for (const k of order) {
            if (!needs.includes(k) || this.stagers[k].has()) continue;
            if (this.ended) return false;
            this.staged.add(k);
            if (!(await this.stagers[k].up())) return false;
        }
        return true;
    }

    // ---------- the end: Done, Skip, Escape, Back button ----------
    async end() {
        if (this.ended) return;
        this.ended = true;
        setDone();
        cancelAnimationFrame(this.raf);
        window.removeEventListener('popstate', this.onPop);
        window.removeEventListener('resize', this.onMove);
        window.removeEventListener('orientationchange', this.onMove);
        window.removeEventListener('scroll', this.onMove, { capture: true });
        window.visualViewport?.removeEventListener('resize', this.onMove);
        if (this.dlg.open) this.dlg.close();
        this.dlg.remove();
        this.card = null;
        // A step still setting up stops at its next check; then take down what the tour set up
        await this.transition.catch(() => {});
        for (const k of ['word', 'study', 'selection']) {
            if (this.staged.has(k)) await this.stagers[k].down();
        }
        this.staged.clear();
        const o = this.opener;
        if (o && o !== document.body && o.isConnected && shown(o)) o.focus({ preventScroll: true });
        this.resolveFinished();
    }
}
