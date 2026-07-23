// bibleApp feature module: study_extras — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.study_extras = {
        // ========== EXPORT NOTES ==========

        exportNotes() {
            const relevant = this.getRelevantNotes();
            if (relevant.length === 0) {
                this.showToast('No notes to export', 'info');
                return;
            }
            const header = this.combinedPlanReading
                ? `Study Notes — ${this.currentPlan?.name || 'Reading Plan'} Day ${this.planDay}`
                : `Study Notes — ${this.currentBook} ${this.currentChapter}`;

            let text = header + '\n' + '='.repeat(header.length) + '\n\n';
            for (const note of relevant) {
                const ref = this.formatNoteReference(note);
                text += `[${ref}]\n`;
                text += note.content + '\n';
                const tags = this.getNoteTagObjects(note.id);
                if (tags.length > 0) {
                    text += 'Tags: ' + tags.map(t => t.name).join(', ') + '\n';
                }
                text += '\n';
            }
            text += `Exported from In the Word — ${new Date().toLocaleDateString()}\n`;

            // Copy to clipboard
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Notes copied to clipboard', 'success');
            }).catch(() => {
                // Fallback: download as file
                const blob = new Blob([text], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `notes-${this.currentBook || 'study'}-${this.currentChapter || ''}.txt`;
                a.click();
                URL.revokeObjectURL(url);
                this.showToast('Notes downloaded', 'success');
            });
        },

        // ========== SCRIPTURE MEMORY ==========

        addToMemory(verseNum, silent = false) {
            if (!this.currentBook || !this.currentChapter) return false;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            if (this.memoryVerses.some(m => m.reference === ref)) {
                if (!silent) this.showToast('Already in memory verses', 'info');
                return false;
            }
            const verseObj = this.verses.find(v => v.verse === verseNum);
            if (!verseObj) return false;
            this.memoryVerses.push({
                reference: ref,
                text: verseObj.text,
                translation: this.translation,
                addedAt: Date.now(),
                // SM-2 spaced repetition fields
                interval: 1,      // days until next review
                ease: 2.5,        // easiness factor
                nextReview: Date.now(),  // due now
                reviewCount: 0
            });
            this.saveMemoryVerses();
            if (!silent) this.showToast('Added to memory verses', 'success');
            return true;
        },

        isInMemory(verseNum) {
            if (!this.currentBook || !this.currentChapter) return false;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            return this.memoryVerses.some(m => m.reference === ref);
        },

        removeFromMemory(reference) {
            this.memoryVerses = this.memoryVerses.filter(m => m.reference !== reference);
            this.saveMemoryVerses();
        },

        saveMemoryVerses() {
            localStorage.setItem('memoryVerses', JSON.stringify(this.memoryVerses));
        },

        openMemoryTool() {
            this.showMemoryTool = true;
            this.showSideMenu = false;
            this.computeDueCards();
            this.memoryActiveCard = null;
            this.memoryStage = 'prompt';
            this.memoryShowAnswer = false;
        },

        computeDueCards() {
            const now = Date.now();
            this.memoryDueCards = this.memoryVerses.filter(m => m.nextReview <= now);
        },

        startMemoryReview() {
            this.computeDueCards();
            if (this.memoryDueCards.length === 0) {
                this.showToast('No verses due for review!', 'info');
                return;
            }
            this.memoryActiveCard = 0;
            this.memoryStage = 'prompt';
            this.memoryShowAnswer = false;
        },

        getCurrentMemoryCard() {
            if (this.memoryActiveCard === null || !this.memoryDueCards.length) return null;
            return this.memoryDueCards[this.memoryActiveCard];
        },

        getMemoryDisplay() {
            const card = this.getCurrentMemoryCard();
            if (!card) return '';
            const text = card.text;
            switch (this.memoryStage) {
                case 'prompt':
                    return '';  // show nothing — just the reference
                case 'firstLetters':
                    return text.split(/\s+/).map(w => {
                        if (!w) return '';
                        const first = w[0];
                        return first + w.slice(1).replace(/[a-zA-Z]/g, '_');
                    }).join(' ');
                case 'blanks':
                    return text.split(/\s+/).map(w => {
                        return w.replace(/[a-zA-Z]/g, '_');
                    }).join(' ');
                case 'reveal':
                    return text;
                default:
                    return '';
            }
        },

        advanceMemoryStage() {
            const stages = ['prompt', 'firstLetters', 'blanks', 'reveal'];
            const idx = stages.indexOf(this.memoryStage);
            if (idx < stages.length - 1) {
                this.memoryStage = stages[idx + 1];
            }
        },

        // SM-2 rating: 0 = forgot, 1 = hard, 2 = good, 3 = easy
        rateMemoryCard(quality) {
            const card = this.getCurrentMemoryCard();
            if (!card) return;
            // Find in main array
            const mainCard = this.memoryVerses.find(m => m.reference === card.reference);
            if (!mainCard) return;

            mainCard.reviewCount++;
            if (quality < 1) {
                // Failed — reset
                mainCard.interval = 1;
                mainCard.ease = Math.max(1.3, mainCard.ease - 0.2);
            } else {
                if (mainCard.reviewCount === 1) {
                    mainCard.interval = 1;
                } else if (mainCard.reviewCount === 2) {
                    mainCard.interval = 3;
                } else {
                    mainCard.interval = Math.round(mainCard.interval * mainCard.ease);
                }
                // Adjust ease
                mainCard.ease = Math.max(1.3, mainCard.ease + (quality === 3 ? 0.15 : quality === 2 ? 0 : -0.15));
            }
            mainCard.nextReview = Date.now() + (mainCard.interval * 86400000);
            this.saveMemoryVerses();

            // Advance to next card
            if (this.memoryActiveCard < this.memoryDueCards.length - 1) {
                this.memoryActiveCard++;
                this.memoryStage = 'prompt';
                this.memoryShowAnswer = false;
            } else {
                // Done with review
                this.memoryActiveCard = null;
                this.memoryStage = 'prompt';
                this.computeDueCards();
                this.showToast('Review complete!', 'success');
            }
        },

        getMemoryStats() {
            const now = Date.now();
            const due = this.memoryVerses.filter(m => m.nextReview <= now).length;
            const total = this.memoryVerses.length;
            const mastered = this.memoryVerses.filter(m => m.interval >= 21).length;
            return { due, total, mastered };
        },

        // ========== READING HISTORY ==========

        addToHistory(reference, translation) {
            if (!reference) return;
            const entry = {
                reference,
                translation: translation || this.translation,
                timestamp: Date.now()
            };
            // Remove duplicate if exists
            this.readingHistory = this.readingHistory.filter(h => h.reference !== reference);
            // Add to front
            this.readingHistory.unshift(entry);
            // Keep max 50 entries
            if (this.readingHistory.length > 50) this.readingHistory = this.readingHistory.slice(0, 50);
            localStorage.setItem('readingHistory', JSON.stringify(this.readingHistory));
        },

        clearHistory() {
            this.readingHistory = [];
            localStorage.setItem('readingHistory', JSON.stringify([]));
        },

        getRecentHistory(limit = 10) {
            return this.readingHistory.slice(0, limit);
        },

        formatHistoryTime(timestamp) {
            const diff = Date.now() - timestamp;
            const mins = Math.floor(diff / 60000);
            if (mins < 1) return 'Just now';
            if (mins < 60) return mins + 'm ago';
            const hours = Math.floor(mins / 60);
            if (hours < 24) return hours + 'h ago';
            const days = Math.floor(hours / 24);
            if (days < 7) return days + 'd ago';
            return new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        },

        // ========== BOOKMARKS ==========

        toggleBookmark(verseNum) {
            if (!this.currentBook || !this.currentChapter) return;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            const existing = this.bookmarks.findIndex(b => b.reference === ref);
            if (existing !== -1) {
                this.bookmarks.splice(existing, 1);
                this.showToast('Bookmark removed', 'info');
            } else {
                const verseObj = this.verses.find(v => v.verse === verseNum);
                this.bookmarks.unshift({
                    reference: ref,
                    book: this.currentBook,
                    chapter: this.currentChapter,
                    verse: verseNum,
                    preview: (verseObj?.text || '').substring(0, 80),
                    translation: this.translation,
                    timestamp: Date.now()
                });
                this.showToast('Verse bookmarked', 'success');
            }
            localStorage.setItem('bible-bookmarks', JSON.stringify(this.bookmarks));
        },

        isBookmarked(verseNum) {
            if (!this.currentBook || !this.currentChapter) return false;
            const ref = `${this.currentBook} ${this.currentChapter}:${verseNum}`;
            return this.bookmarks.some(b => b.reference === ref);
        },

        removeBookmark(reference) {
            this.bookmarks = this.bookmarks.filter(b => b.reference !== reference);
            localStorage.setItem('bible-bookmarks', JSON.stringify(this.bookmarks));
        },

        goToBookmark(bookmark) {
            this.loadReference(bookmark.reference);
        },
};
