// bibleApp feature module: selection — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.selection = {
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
