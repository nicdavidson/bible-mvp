// bibleApp feature module: menus — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};

// About > Sources and rights. How a rights holder reaches us: the ONE place to change it.
// When the owner has a mailbox, set `email`; the page then shows the email first and the
// GitHub issue link second. No sign-in is needed for either (the feedback form needs one).
const RIGHTS_CONTACT = {
    email: null,
    issueUrl: 'https://github.com/nicdavidson/bible-mvp/issues/new',
    licensesUrl: 'https://github.com/nicdavidson/bible-mvp/blob/master/LICENSES.md',
};
const RIGHTS_ISSUE_TITLE = 'Rights enquiry: <work>';
const RIGHTS_ISSUE_BODY = [
    '**Work** (title and author, and where it appears in the app):',
    '',
    '**Claimant** (who holds the rights, and your relation to them):',
    '',
    '**Basis of the claim** (for example registration or renewal details, publication date):',
    '',
    '**Contact** (how we can reach you; optional, this issue is public):',
    '',
].join('\n');

// [{ kind, href, label }] in display order: email first when one is configured.
function rightsContactLinks(contact = RIGHTS_CONTACT) {
    const links = [];
    if (contact.email) {
        links.push({
            kind: 'email',
            href: `mailto:${contact.email}?subject=${encodeURIComponent('Rights enquiry')}`,
            label: `Email ${contact.email}`,
        });
    }
    if (contact.issueUrl) {
        const q = new URLSearchParams({ title: RIGHTS_ISSUE_TITLE, body: RIGHTS_ISSUE_BODY });
        links.push({
            kind: 'issue',
            href: `${contact.issueUrl}?${q.toString()}`,
            label: contact.email ? 'Or open a public issue on GitHub' : 'Open a rights enquiry on GitHub (public issue)',
        });
    }
    return links;
}
window.BibleRights = { RIGHTS_CONTACT, rightsContactLinks };

window.BibleModules.menus = {
        // About > Sources and rights: commentary sources from /api/commentary/sources
        aboutSources: null,        // null = not loaded yet
        aboutSourcesError: false,
        rightsLinks: rightsContactLinks(),
        rightsLicensesUrl: RIGHTS_CONTACT.licensesUrl,

        // ========== Side Menu Navigation ==========

        // Navigate to a view from side menu
        navigateTo(view) {
            this.currentView = view;
            this.showSideMenu = false;

            if (view === 'reader') {
                // Exit plan reading mode and go back to normal Bible view
                this.exitPlanReading();
            } else if (view === 'plans') {
                this.openReadingPlan();
            }
        },

        // Open settings from side menu
        openSettingsFromMenu(tab = 'general') {
            this.showSideMenu = false;
            this.openSettings(tab);
        },

        // Open Guide modal
        openGuide() {
            this.showSideMenu = false;
            this.showGuide = true;
        },

        // Open About modal; section 'sources' scrolls to Sources and rights (/?about=sources)
        openAbout(section = null) {
            this.showSideMenu = false;
            this.showAbout = true;
            this.loadAboutSources();
            if (section === 'sources') {
                this.$nextTick(() => {
                    const h = document.getElementById('about-sources-h');
                    if (!h) return;
                    h.scrollIntoView({ block: 'start' });
                    h.focus({ preventScroll: true });
                });
            }
        },

        async loadAboutSources() {
            if (this.aboutSources) return;
            this.aboutSourcesError = false;
            try {
                const r = await fetch('/api/commentary/sources');
                if (!r.ok) throw new Error(String(r.status));
                this.aboutSources = (await r.json()).sources || [];
            } catch {
                this.aboutSourcesError = true;
            }
        },

        // "John Gill (1697-1771), 1746"
        aboutSourceByline(s) {
            return [s.author, s.year].filter(Boolean).join(', ');
        },

        // Open Feedback modal from About
        openFeedbackFromAbout() {
            this.showAbout = false;
            this.showFeedback = true;
        },

        openFeedbackFromMenu() {
            this.showSideMenu = false;
            this.showFeedback = true;
        },

        // Open Share Jesus modal
        openShareJesus() {
            this.showSideMenu = false;
            this.showShareJesus = true;
        },

        // Go to verse from Share Jesus modal
        goToVerseFromModal(ref) {
            this.navigate(ref, { kind: 'jump' });
        },

        // ========== Single Verse View (Reusable) ==========

        // Open single verse view with a list of verses
        async openSingleVerseView(verses, options = {}) {
            this.singleVerseList = verses;
            this.singleVerseIndex = 1;
            this.singleVersePrompt = options.prompt || '';
            this.singleVerseOnFinish = options.onFinish || null;
            this.singleVerseMode = true;
            await this.loadSingleVerse(1);
        },

        // Get current verse info
        getCurrentSingleVerse() {
            return this.singleVerseList[this.singleVerseIndex - 1] || { ref: '' };
        },

        // Load verse text from API
        async loadSingleVerse(index) {
            const verse = this.singleVerseList[index - 1];
            if (!verse) return;

            this.singleVerseLoading = true;
            this.singleVerseText = '';

            try {
                const response = await fetch(`/api/passage/${encodeURIComponent(verse.ref)}?translation=${this.translation}`);
                if (response.ok) {
                    const data = await response.json();
                    // Filter to only the highlighted (requested) verses, not the full chapter
                    const highlightedVerses = data.highlighted_verses || [];
                    const filteredVerses = highlightedVerses.length > 0
                        ? data.verses.filter(v => highlightedVerses.includes(v.verse))
                        : data.verses;
                    this.singleVerseText = filteredVerses.map(v => v.text).join(' ');
                }
            } catch (err) {
                console.error('Failed to load verse:', err);
                this.singleVerseText = 'Failed to load verse. Please try again.';
            } finally {
                this.singleVerseLoading = false;
            }
        },

        // Navigate to next verse
        async nextSingleVerse() {
            if (this.singleVerseIndex < this.singleVerseList.length) {
                this.singleVerseIndex++;
                await this.loadSingleVerse(this.singleVerseIndex);
            }
        },

        // Navigate to previous verse
        async prevSingleVerse() {
            if (this.singleVerseIndex > 1) {
                this.singleVerseIndex--;
                await this.loadSingleVerse(this.singleVerseIndex);
            }
        },

        // Go to specific verse
        async goToSingleVerse(index) {
            this.singleVerseIndex = index;
            await this.loadSingleVerse(index);
        },

        // Exit single verse mode
        exitSingleVerseMode() {
            this.singleVerseMode = false;
            if (this.singleVerseOnFinish) {
                this.singleVerseOnFinish();
            }
        },

        // Finish viewing all verses
        finishSingleVerseMode() {
            this.singleVerseMode = false;
            this.singleVerseFullPassage = false;
            if (this.singleVerseOnFinish) {
                this.singleVerseOnFinish();
            }
        },

        // View full passage from single verse mode
        async viewFullPassageFromSingleVerse() {
            const verse = this.getCurrentSingleVerse();
            if (!verse) return;

            // Hide single verse overlay and show full passage bar
            this.singleVerseMode = false;
            this.singleVerseFullPassage = true;

            // Read the passage with the verse highlighted; the bar above is the way back
            await this.navigate(verse.ref, { kind: 'read' });
        },

        // Return to single verse mode from full passage view
        returnToSingleVerseMode() {
            this.singleVerseFullPassage = false;
            this.singleVerseMode = true;
        },
};
