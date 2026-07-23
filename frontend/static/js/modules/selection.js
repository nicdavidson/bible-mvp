// bibleApp feature module: selection — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.selection = {
        // ========== MULTI-VERSE SELECTION METHODS ==========

        // Toggle note edit mode
        toggleNoteEditMode() {
            this.noteEditMode = !this.noteEditMode;
            if (this.noteEditMode) {
                // Start with currently highlighted verse
                this.selectedVerses = this.highlightedVerses.length > 0
                    ? [...this.highlightedVerses]
                    : [];
            } else {
                this.selectedVerses = [];
            }
        },

        // Handle verse selection in note edit mode
        handleVerseSelection(verseNum, event) {
            if (!this.noteEditMode) return;

            // Shift+click for range selection
            if (event.shiftKey && this.selectedVerses.length > 0) {
                const lastSelected = this.selectedVerses[this.selectedVerses.length - 1];
                const start = Math.min(lastSelected, verseNum);
                const end = Math.max(lastSelected, verseNum);
                // Select all verses in range
                for (let v = start; v <= end; v++) {
                    if (!this.selectedVerses.includes(v)) {
                        this.selectedVerses.push(v);
                    }
                }
            } else {
                // Toggle single verse
                const idx = this.selectedVerses.indexOf(verseNum);
                if (idx >= 0) {
                    this.selectedVerses.splice(idx, 1);
                } else {
                    this.selectedVerses.push(verseNum);
                }
            }

            // Sort selection
            this.selectedVerses.sort((a, b) => a - b);
        },

        // Check if verse is selected for note
        isVerseSelectedForNote(verseNum) {
            return this.selectedVerses.includes(verseNum);
        },

        // Get selected verse range as string
        getSelectedVerseRange() {
            if (this.selectedVerses.length === 0) return '';
            const sorted = [...this.selectedVerses].sort((a, b) => a - b);
            if (sorted.length === 1) return `${sorted[0]}`;

            // Find contiguous ranges
            const ranges = [];
            let start = sorted[0];
            let end = sorted[0];

            for (let i = 1; i < sorted.length; i++) {
                if (sorted[i] === end + 1) {
                    end = sorted[i];
                } else {
                    ranges.push(start === end ? `${start}` : `${start}-${end}`);
                    start = end = sorted[i];
                }
            }
            ranges.push(start === end ? `${start}` : `${start}-${end}`);

            return ranges.join(', ');
        },

        // Get first and last selected verses
        getSelectedVerseStart() {
            if (this.selectedVerses.length === 0) return this.highlightedVerses[0] || 1;
            return Math.min(...this.selectedVerses);
        },

        getSelectedVerseEnd() {
            if (this.selectedVerses.length === 0) return this.highlightedVerses[0] || 1;
            return Math.max(...this.selectedVerses);
        },

        // In combined plan mode multiple chapters are concatenated into one
        // verses array, so a bare verse number is ambiguous — selection is
        // additionally scoped to the chapter it was made in.
        verseInSelectionScope(verseObj) {
            if (!this.combinedPlanReading || !this.selectionContext) return true;
            return !!verseObj && verseObj._book === this.selectionContext.book
                && verseObj._chapter === this.selectionContext.chapter;
        },

        // Check if a verse should be highlighted
        isVerseHighlighted(verseNum, verseObj) {
            return this.highlightedVerses.includes(verseNum) && this.verseInSelectionScope(verseObj);
        },

        // Update URL with clean path format (/Book/Chapter/Verse or /plan/PlanId/Day)
        // usePush=true creates a new history entry (for chapter navigation);
        // usePush=false uses replaceState (for verse selection within same chapter)
        updateURL(usePush = false) {
            // If in combined plan reading mode, use plan URL format
            if (this.combinedPlanReading && this.currentPlan) {
                const path = `/plan/${this.currentPlan.id}/${this.planDay}`;
                window.history.pushState({}, '', path);
                return;
            }

            if (!this.currentBook || !this.currentChapter) return;

            const bookSlug = this.currentBook.replace(/\s+/g, '-');
            const verse = this.highlightedVerses.length === 1 ? this.highlightedVerses[0] : null;
            const path = verse
                ? `/${bookSlug}/${this.currentChapter}/${verse}`
                : `/${bookSlug}/${this.currentChapter}`;

            if (usePush) {
                window.history.pushState({}, '', path);
            } else {
                window.history.replaceState({}, '', path);
            }
        },

        // Copy verse to clipboard
        async copyVerse(verse) {
            const text = `"${verse.text}" — ${this.currentBook} ${this.currentChapter}:${verse.verse} ${this.translation}`;

            try {
                await navigator.clipboard.writeText(text);
                this.copyFeedback = verse.verse;
                setTimeout(() => {
                    this.copyFeedback = null;
                }, 1500);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        },

        // Dismiss source text warning
        dismissSourceTextWarning() {
            this.sourceTextWarningDismissed = true;
            localStorage.setItem('sourceTextWarningDismissed', 'true');
        },

        // Get reading progress percentage
        getReadingProgress() {
            if (!this.verses.length || !this.highlightedVerses.length) return 0;
            const currentVerse = this.highlightedVerses[0];
            const maxVerse = Math.max(...this.verses.map(v => v.verse));
            return Math.round((currentVerse / maxVerse) * 100);
        },
};
