// bibleApp feature module: feedback — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.feedback = {
        // ========== Feedback/Bug Report Functions ==========

        // Handle screenshot file selection
        handleScreenshotSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.feedbackScreenshot = file;
                // Create preview URL
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.feedbackScreenshotPreview = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        },

        // Clear screenshot
        clearScreenshot() {
            this.feedbackScreenshot = null;
            this.feedbackScreenshotPreview = '';
        },

        // Reset feedback form
        resetFeedbackForm() {
            this.feedbackCategory = 'bug';
            this.feedbackDescription = '';
            this.feedbackVerseRef = '';
            this.feedbackTranslation = '';
            this.feedbackAccuracyType = '';
            this.feedbackScreenshot = null;
            this.feedbackScreenshotPreview = '';
            this.feedbackSubmitting = false;
            this.feedbackSuccess = false;
            this.feedbackError = null;
        },

        // Submit feedback
        async submitFeedback() {
            if (!this.authUser) {
                this.feedbackError = 'Please sign in to submit feedback';
                return;
            }

            if (!this.feedbackDescription.trim()) {
                this.feedbackError = 'Please provide a description';
                return;
            }

            this.feedbackSubmitting = true;
            this.feedbackError = null;

            try {
                let screenshotPath = null;

                // Upload screenshot if present (for bugs)
                if (this.feedbackCategory === 'bug' && this.feedbackScreenshot) {
                    try {
                        screenshotPath = await SupabaseAuth.uploadBugScreenshot(this.feedbackScreenshot);
                    } catch (err) {
                        console.warn('Screenshot upload failed, continuing without:', err);
                        // Continue without screenshot - don't fail the whole submission
                    }
                }

                // Build report object
                const report = {
                    category: this.feedbackCategory,
                    description: this.feedbackDescription.trim(),
                    screenshotPath: screenshotPath,
                    currentUrl: window.location.href
                };

                // Add accuracy-specific fields if applicable
                if (this.feedbackCategory === 'accuracy') {
                    report.verseReference = this.feedbackVerseRef || null;
                    report.translation = this.feedbackTranslation || null;
                    report.accuracyType = this.feedbackAccuracyType || null;
                }

                // Submit to Supabase
                await SupabaseAuth.submitBugReport(report);

                this.feedbackSuccess = true;
                this.showToast('Feedback submitted. Thank you!', 'success');

            } catch (err) {
                console.error('Failed to submit feedback:', err);
                this.feedbackError = err.message || 'Failed to submit feedback. Please try again.';
            } finally {
                this.feedbackSubmitting = false;
            }
        },

        // Search - debounced live search
        handleSearchInput() {
            // Clear previous timer
            if (this.searchDebounceTimer) {
                clearTimeout(this.searchDebounceTimer);
            }

            // Reset selection when typing
            this.selectedResultIndex = -1;

            // Debounce search (300ms)
            this.searchDebounceTimer = setTimeout(() => {
                this.performSearch();
            }, 300);
        },

        async performSearch() {
            const query = this.searchQuery.trim();

            // Need at least 2 characters
            if (query.length < 2) {
                this.searchResults = [];
                this.searchPerformed = false;
                return;
            }

            this.searchLoading = true;
            this.searchPerformed = true;
            this.selectedResultIndex = -1;

            try {
                const response = await fetch(
                    `/api/search?q=${encodeURIComponent(query)}&scope=${this.searchScope}`
                );

                if (response.ok) {
                    const data = await response.json();
                    this.searchResults = data.results || [];
                    this.searchWordInfo = data.word_info || null;
                }
            } catch (err) {
                console.error('Search failed:', err);
                this.searchResults = [];
            } finally {
                this.searchLoading = false;
            }
        },

        // Handle keyboard navigation in search results
        handleSearchKeydown(event) {
            const resultCount = this.searchResults.length;

            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    if (resultCount > 0) {
                        this.selectedResultIndex = Math.min(
                            this.selectedResultIndex + 1,
                            resultCount - 1
                        );
                        this.scrollToSelectedResult();
                    }
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    if (resultCount > 0) {
                        this.selectedResultIndex = Math.max(
                            this.selectedResultIndex - 1,
                            0
                        );
                        this.scrollToSelectedResult();
                    }
                    break;
                case 'Enter':
                    if (this.selectedResultIndex >= 0 && this.selectedResultIndex < resultCount) {
                        event.preventDefault();
                        this.goToSearchResult(this.searchResults[this.selectedResultIndex]);
                    } else if (resultCount > 0) {
                        // If no selection, go to first result
                        event.preventDefault();
                        this.goToSearchResult(this.searchResults[0]);
                    }
                    break;
                case 'Escape':
                    this.showSearch = false;
                    break;
            }
        },

        scrollToSelectedResult() {
            this.$nextTick(() => {
                const selected = document.querySelector('.search-result.selected');
                if (selected) {
                    selected.scrollIntoView({ block: 'nearest' });
                }
            });
        },

        // Get grouped search results
        getGroupedResults() {
            const groups = {
                verse: [],
                commentary: []
            };
            for (const result of this.searchResults) {
                if (result.type === 'verse') {
                    groups.verse.push(result);
                } else if (result.type === 'commentary') {
                    groups.commentary.push(result);
                }
            }
            return groups;
        },

        // Go to search result
        goToSearchResult(result) {
            if (result.book && result.chapter) {
                const ref = result.verse
                    ? `${result.book} ${result.chapter}:${result.verse}`
                    : `${result.book} ${result.chapter}`;
                this.loadReference(ref);
                this.showSearch = false;
                this.searchQuery = '';
                this.searchResults = [];
                this.searchPerformed = false;
            }
        },

        // Reset search state when opening
        openSearch() {
            this.showSearch = true;
            this.searchResults = [];
            this.searchWordInfo = null;
            this.searchPerformed = false;
            this.selectedResultIndex = -1;
            if (this.searchDebounceTimer) {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = null;
            }
            this.$nextTick(() => this.$refs.searchInput?.focus());
        },

        // Auth methods
        async initAuth() {
            try {
                if (window.SupabaseAuth) {
                    // Check for existing session
                    const user = await window.SupabaseAuth.getUser();
                    this.authUser = user;

                    // If already signed in, load plan progress from Supabase
                    if (user) {
                        this.loadPlanProgressFromSupabase();
                    }

                    // Listen for auth changes
                    window.SupabaseAuth.onAuthStateChange((event, user) => {
                        this.authUser = user;
                        if (event === 'SIGNED_IN') {
                            this.loadNotes();
                            this.loadTags();
                            this.loadPlanProgressFromSupabase();
                            this.showToast('Signed in successfully', 'success');
                        } else if (event === 'SIGNED_OUT') {
                            this.loadNotes();
                            this.loadTags();
                            // Clear synced status when signed out
                            this.planProgressSynced = false;
                        }
                    });
                }
            } catch (err) {
                console.warn('Auth initialization failed:', err);
            }
        },

        async handleSignIn() {
            this.authError = null;
            this.authSuccess = null;
            this.authLoading = true;

            try {
                await window.SupabaseAuth.signIn(this.authEmail, this.authPassword);
                this.authEmail = '';
                this.authPassword = '';
            } catch (err) {
                this.authError = err.message || 'Failed to sign in';
            } finally {
                this.authLoading = false;
            }
        },

        async handleSignUp() {
            this.authError = null;
            this.authSuccess = null;

            if (this.authPassword !== this.authPasswordConfirm) {
                this.authError = 'Passwords do not match';
                return;
            }

            if (this.authPassword.length < 6) {
                this.authError = 'Password must be at least 6 characters';
                return;
            }

            this.authLoading = true;

            try {
                await window.SupabaseAuth.signUp(this.authEmail, this.authPassword);
                this.authSuccess = 'Check your email to confirm your account';
                this.authEmail = '';
                this.authPassword = '';
                this.authPasswordConfirm = '';
            } catch (err) {
                this.authError = err.message || 'Failed to create account';
            } finally {
                this.authLoading = false;
            }
        },

        async handleSignOut() {
            this.authLoading = true;
            try {
                await window.SupabaseAuth.signOut();
                this.authUser = null;
                await this.loadNotes();  // Reload local notes
                this.showToast('Signed out', 'info');
            } catch (err) {
                this.showToast('Failed to sign out', 'error');
            } finally {
                this.authLoading = false;
            }
        },

        async handleForgotPassword() {
            if (!this.authEmail) {
                this.authError = 'Enter your email address first';
                return;
            }

            this.authLoading = true;
            this.authError = null;

            try {
                await window.SupabaseAuth.resetPassword(this.authEmail);
                this.authSuccess = 'Check your email for password reset link';
            } catch (err) {
                this.authError = err.message || 'Failed to send reset email';
            } finally {
                this.authLoading = false;
            }
        },

        // Notes (Supabase for logged-in users, localStorage for guests)
        async loadNotes() {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Load from Supabase
                    this.notes = await window.SupabaseAuth.fetchUserNotes();
                } else {
                    // Load from localStorage (guest mode)
                    const saved = localStorage.getItem('bible-notes');
                    this.notes = saved ? JSON.parse(saved) : [];
                }
            } catch (err) {
                console.error('Failed to load notes:', err);
                // Fall back to localStorage
                const saved = localStorage.getItem('bible-notes');
                this.notes = saved ? JSON.parse(saved) : [];
            }
            this.rebuildVerseColorMap();
        },

        // Note editing state
        noteEndVerse: null,
        showNoteRange: false,

        // Get the current start verse for notes
        getNoteStartVerse() {
            return this.highlightedVerses.length > 0 ? this.highlightedVerses[0] : 1;
        },

        // Format note reference display
        formatNoteReference(note) {
            if (note.endVerse && note.endVerse !== note.startVerse) {
                return `${note.book} ${note.chapter}:${note.startVerse}-${note.endVerse}`;
            }
            return `${note.book} ${note.chapter}:${note.startVerse}`;
        },

        // Format note content with clickable Bible references
        formatNoteContent(content) {
            return linkifyBibleReferences(content);
        },

        // Handle clicks on Bible reference links in notes
        handleNoteRefClick(event) {
            const link = event.target.closest('.note-ref');
            if (link) {
                event.preventDefault();
                const ref = link.dataset.ref;
                if (ref) {
                    this.loadReference(ref);
                }
            }
        },

        // Check if note is in current chapter (or any chapter in combined plan reading mode)
        noteInCurrentChapter(note) {
            // In combined plan reading mode, check against all chapters being read
            if (this.combinedPlanReading && this.planReadingChapters.length > 0) {
                return this.planReadingChapters.some(ch =>
                    ch.book === note.book && ch.chapter === note.chapter
                );
            }
            // Normal mode: check current book/chapter
            return note.book === this.currentBook && note.chapter === this.currentChapter;
        },

        // Check if note applies to active verse (from scroll or click)
        noteMatchesActiveVerse(note) {
            const activeVerse = this.getActiveVerse();
            if (!activeVerse) return true;  // If no active verse, all match
            const start = note.startVerse || 1;
            const end = note.endVerse || start;
            return activeVerse >= start && activeVerse <= end;
        },

        // Get the currently active verse (from click or scroll)
        getActiveVerse() {
            // Clicked verse takes priority
            if (this.highlightedVerses.length > 0) {
                return this.highlightedVerses[0];
            }
            // Otherwise use scroll-tracked verse
            return this.scrollActiveVerse;
        },

        // Get all notes for the current chapter, sorted with active verse notes first.
        // Memoized: called 10+ times per render from templates. The key covers every
        // input the result depends on; noteDataVersion is bumped on note/tag changes.
        getRelevantNotes() {
            const key = [
                this.noteDataVersion,
                this.getActiveVerse(),
                this.currentBook,
                this.currentChapter,
                this.combinedPlanReading
                    ? this.planReadingChapters.map(c => `${c.book}|${c.chapter}`).join(',')
                    : ''
            ].join('~');
            if (key === _relevantNotesKey) return _relevantNotesCache;

            // Filter to current chapter, exclude highlight-only notes (no content)
            const chapterNotes = this.notes.filter(note =>
                this.noteInCurrentChapter(note) && (note.content?.trim())
            );

            // Sort: active verse notes first, then by verse number
            _relevantNotesCache = chapterNotes.sort((a, b) => {
                const aActive = this.noteMatchesActiveVerse(a);
                const bActive = this.noteMatchesActiveVerse(b);

                if (aActive && !bActive) return -1;
                if (!aActive && bActive) return 1;

                // Same active status: sort by verse
                return (a.startVerse || 1) - (b.startVerse || 1);
            });
            _relevantNotesKey = key;
            return _relevantNotesCache;
        },

        async saveNote() {
            if (!this.currentNote.trim() || !this.currentBook) return;

            // Use selected verses if in note edit mode, otherwise use highlighted verse
            const startVerse = this.noteEditMode && this.selectedVerses.length > 0
                ? this.getSelectedVerseStart()
                : this.getNoteStartVerse();
            const endVerse = this.noteEditMode && this.selectedVerses.length > 0
                ? this.getSelectedVerseEnd()
                : (this.showNoteRange && this.noteEndVerse ? parseInt(this.noteEndVerse) : startVerse);

            const noteData = {
                book: this.currentBook,
                chapter: this.currentChapter,
                startVerse: startVerse,
                endVerse: endVerse,
                content: this.currentNote
            };

            try {
                let savedNoteId;
                if (this.authUser && window.SupabaseAuth) {
                    // Save to Supabase
                    const savedNote = await window.SupabaseAuth.saveUserNote(noteData);
                    this.notes.unshift(savedNote);
                    savedNoteId = savedNote.id;
                } else {
                    // Save to localStorage (guest mode)
                    const note = {
                        id: Date.now(),
                        ...noteData,
                        created_at: new Date().toISOString(),
                        synced: false
                    };
                    this.notes.unshift(note);
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                    savedNoteId = note.id;
                }
                this.rebuildVerseColorMap();

                // Apply pending tags to the new note
                if (this.pendingNoteTags.length > 0 && savedNoteId) {
                    for (const tagId of this.pendingNoteTags) {
                        await this.toggleNoteTag(savedNoteId, tagId);
                    }
                }

                this.currentNote = '';
                this.noteEndVerse = null;
                this.showNoteRange = false;
                this.noteEditMode = false;
                this.selectedVerses = [];
                this.pendingNoteTags = [];
            } catch (err) {
                console.error('Failed to save note:', err);
                this.showToast('Failed to save note', 'error');
            }
        },

        // Delete a note
        async deleteNote(noteId) {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Delete from Supabase
                    await window.SupabaseAuth.deleteUserNote(noteId);
                }
                // Always remove from local state
                this.notes = this.notes.filter(n => n.id !== noteId);
                this.rebuildVerseColorMap();

                // Update localStorage for guests
                if (!this.authUser) {
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                }
            } catch (err) {
                console.error('Failed to delete note:', err);
                this.showToast('Failed to delete note', 'error');
            }
        },

        // Start editing a note
        startEditNote(note) {
            this.editingNoteId = note.id;
            this.editingNoteContent = note.content;
        },

        // Cancel editing a note
        cancelEditNote() {
            this.editingNoteId = null;
            this.editingNoteContent = '';
        },

        // Save edited note
        async saveEditNote(note) {
            if (!this.editingNoteContent.trim()) return;

            try {
                const updatedContent = this.editingNoteContent.trim();

                if (this.authUser && window.SupabaseAuth) {
                    // Update in Supabase
                    await window.SupabaseAuth.updateUserNote(note.id, { content: updatedContent });
                }

                // Update local state
                const noteIndex = this.notes.findIndex(n => n.id === note.id);
                if (noteIndex !== -1) {
                    this.notes[noteIndex].content = updatedContent;
                }
                this.rebuildVerseColorMap();  // content changes affect getRelevantNotes (empty-note filter)

                // Update localStorage for guests
                if (!this.authUser) {
                    localStorage.setItem('bible-notes', JSON.stringify(this.notes));
                }

                // Clear editing state
                this.editingNoteId = null;
                this.editingNoteContent = '';
            } catch (err) {
                console.error('Failed to update note:', err);
                this.showToast('Failed to update note', 'error');
            }
        },

        // Format date
        formatDate(isoString) {
            return new Date(isoString).toLocaleDateString();
        },
};
