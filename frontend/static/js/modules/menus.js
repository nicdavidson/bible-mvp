// bibleApp feature module: menus — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.menus = {
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

        // Exit plan reading mode and return to normal Bible view
        exitPlanReading() {
            this.combinedPlanReading = false;
            this.planReadingMode = false;
            this.wasInPlanReading = false;
            // Clear the combined reading data
            this.planReadingSections = [];
            this.planReadingChapters = [];
            this.combinedCrossRefs = [];
            this.combinedCommentary = [];
            this.combinedNotes = [];
            // Keep the current reference if we have one, otherwise go to welcome view
            if (!this.currentBook) {
                this.verses = [];
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

        // Open About modal
        openAbout() {
            this.showSideMenu = false;
            this.showAbout = true;
        },

        // Open Feedback modal from About
        openFeedbackFromAbout() {
            this.showAbout = false;
            this.showFeedback = true;
        },

        // Open Share Jesus modal
        openShareJesus() {
            this.showSideMenu = false;
            this.showShareJesus = true;
        },

        // Go to verse from Share Jesus modal
        goToVerseFromModal(ref) {
            this.showShareJesus = false;
            this.exitPlanReading();
            this.referenceInput = ref;
            this.loadPassage();
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

            // Navigate to the passage with the verse highlighted
            this.referenceInput = verse.ref;
            await this.loadPassage();
        },

        // Return to single verse mode from full passage view
        returnToSingleVerseMode() {
            this.singleVerseFullPassage = false;
            this.singleVerseMode = true;
        },
};
