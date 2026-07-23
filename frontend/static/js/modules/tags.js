// bibleApp feature module: tags — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.tags = {
        // ========== TAG METHODS ==========

        // Load user tags
        async loadTags() {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    // Load from Supabase
                    this.tags = await window.SupabaseAuth.fetchUserTags();
                    this.noteTags = await window.SupabaseAuth.fetchAllNoteTags();
                } else {
                    // Load from localStorage (guest mode)
                    const savedTags = localStorage.getItem('bible-tags');
                    this.tags = savedTags ? JSON.parse(savedTags) : [];
                    const savedNoteTags = localStorage.getItem('bible-note-tags');
                    this.noteTags = savedNoteTags ? JSON.parse(savedNoteTags) : {};
                }
            } catch (err) {
                console.error('Failed to load tags:', err);
                // Fall back to localStorage
                const savedTags = localStorage.getItem('bible-tags');
                this.tags = savedTags ? JSON.parse(savedTags) : [];
            }
            this.rebuildVerseColorMap();
        },

        // Create a new tag
        async createTag() {
            if (!this.newTagName.trim()) return;

            const tagData = {
                name: this.newTagName.trim(),
                color: this.newTagColor
            };

            try {
                if (this.authUser && window.SupabaseAuth) {
                    const savedTag = await window.SupabaseAuth.createUserTag(tagData.name, tagData.color);
                    this.tags.push(savedTag);
                } else {
                    // Guest mode - save to localStorage
                    const tag = {
                        id: Date.now(),
                        ...tagData,
                        sortOrder: this.tags.length,
                        synced: false
                    };
                    this.tags.push(tag);
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                }

                this.newTagName = '';
                this.newTagColor = '#ef4444';
            } catch (err) {
                console.error('Failed to create tag:', err);
                this.showToast('Failed to create tag', 'error');
            }
        },

        // Update a tag
        async updateTag(tag) {
            try {
                if (this.authUser && window.SupabaseAuth) {
                    await window.SupabaseAuth.updateUserTag(tag.id, {
                        name: tag.name,
                        color: tag.color,
                        sortOrder: tag.sortOrder
                    });
                } else {
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                }
                this.editingTag = null;
                this.rebuildVerseColorMap();  // tag color may have changed
            } catch (err) {
                console.error('Failed to update tag:', err);
                this.showToast('Failed to update tag', 'error');
            }
        },

        // Delete a tag
        async deleteTag(tagId) {
            if (!confirm('Delete this tag? It will be removed from all notes.')) return;

            try {
                if (this.authUser && window.SupabaseAuth) {
                    await window.SupabaseAuth.deleteUserTag(tagId);
                }
                this.tags = this.tags.filter(t => t.id !== tagId);

                // Remove from note tags
                for (const noteId of Object.keys(this.noteTags)) {
                    this.noteTags[noteId] = this.noteTags[noteId].filter(tid => tid !== tagId);
                }

                if (!this.authUser) {
                    localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                    localStorage.setItem('bible-note-tags', JSON.stringify(this.noteTags));
                }
                this.rebuildVerseColorMap();
            } catch (err) {
                console.error('Failed to delete tag:', err);
                this.showToast('Failed to delete tag', 'error');
            }
        },

        // Get tags for a note
        getNoteTagObjects(noteId) {
            const tagIds = this.noteTags[noteId] || [];
            return this.tags.filter(t => tagIds.includes(t.id));
        },

        // Toggle a tag on a note
        async toggleNoteTag(noteId, tagId) {
            const currentTags = this.noteTags[noteId] || [];
            const hasTag = currentTags.includes(tagId);

            try {
                if (hasTag) {
                    // Remove tag
                    if (this.authUser && window.SupabaseAuth) {
                        await window.SupabaseAuth.removeTagFromNote(noteId, tagId);
                    }
                    this.noteTags[noteId] = currentTags.filter(tid => tid !== tagId);
                } else {
                    // Add tag
                    if (this.authUser && window.SupabaseAuth) {
                        await window.SupabaseAuth.addTagToNote(noteId, tagId);
                    }
                    if (!this.noteTags[noteId]) this.noteTags[noteId] = [];
                    this.noteTags[noteId].push(tagId);
                }

                if (!this.authUser) {
                    localStorage.setItem('bible-note-tags', JSON.stringify(this.noteTags));
                }
                this.rebuildVerseColorMap();
            } catch (err) {
                console.error('Failed to toggle note tag:', err);
                this.showToast('Failed to update tags', 'error');
            }
        },

        // Check if a note has a specific tag
        noteHasTag(noteId, tagId) {
            return (this.noteTags[noteId] || []).includes(tagId);
        },

        // Toggle a pending tag for new note creation
        togglePendingTag(tagId) {
            const idx = this.pendingNoteTags.indexOf(tagId);
            if (idx >= 0) {
                this.pendingNoteTags.splice(idx, 1);
            } else {
                this.pendingNoteTags.push(tagId);
            }
        },

        // Check if a tag is pending for new note
        isPendingTag(tagId) {
            return this.pendingNoteTags.includes(tagId);
        },

        // Rebuild the precomputed verse -> tag colors map. Must be called after
        // any note/tag/note-tag mutation (and on passage/plan load for safety).
        // Keys are always 'Book|Chapter|Verse' so combined plan mode (verses
        // carry their own _book/_chapter) and normal mode share one map, and
        // highlights paint per-chapter in combined mode.
        rebuildVerseColorMap() {
            const map = {};
            for (const note of this.notes) {
                const tagIds = this.noteTags[note.id] || [];
                if (tagIds.length === 0) continue;
                // Same ordering as getNoteTagObjects: this.tags order
                const colors = this.tags.filter(t => tagIds.includes(t.id)).map(t => t.color);
                if (colors.length === 0) continue;
                const start = note.startVerse || 1;
                const end = note.endVerse || start;
                for (let v = start; v <= end; v++) {
                    const key = `${note.book}|${note.chapter}|${v}`;
                    let bucket = map[key];
                    if (!bucket) bucket = map[key] = [];
                    for (const color of colors) {
                        if (bucket.length < 3 && !bucket.includes(color)) bucket.push(color); // Max 3 dots
                    }
                }
            }
            this.verseColorMap = map;  // fresh object → Alpine re-renders dependents
            this.noteDataVersion++;    // invalidates getRelevantNotes memo
        },

        // Get tag colors for a verse (from notes on that verse).
        // O(1) lookup into the precomputed verseColorMap.
        getVerseTagColors(verseNum, verseObj) {
            // Combined plan mode: each verse carries its own _book/_chapter;
            // currentBook/currentChapter only track the last selection there.
            const book = verseObj?._book ?? this.currentBook;
            const chapter = verseObj?._chapter ?? this.currentChapter;
            return this.verseColorMap[`${book}|${chapter}|${verseNum}`] || EMPTY_COLORS;
        },


        // ========== VERSE HIGHLIGHTING (via tags) ==========

        getVerseHighlightColor(verseNum, verseObj) {
            // Returns the first tag color on this verse (used for background)
            const colors = this.getVerseTagColors(verseNum, verseObj);
            return colors.length > 0 ? colors[0] : null;
        },

        toggleHighlightPicker(verseNum) {
            this.showHighlightPicker = this.showHighlightPicker === verseNum ? null : verseNum;
        },

        async quickHighlight(verseNum, color) {
            if (!this.currentBook || !this.currentChapter) return;
            this.showHighlightPicker = null;

            // Find or create a tag with this color
            let tag = this.tags.find(t => t.color === color);
            if (!tag) {
                // Auto-create a highlight tag for this color
                const colorNames = {
                    '#fef08a': 'Yellow', '#bbf7d0': 'Green', '#bfdbfe': 'Blue',
                    '#fbcfe8': 'Pink', '#fed7aa': 'Orange', '#e9d5ff': 'Purple'
                };
                const name = colorNames[color] || 'Highlight';
                const tagData = { name, color };
                try {
                    if (this.authUser && window.SupabaseAuth) {
                        tag = await window.SupabaseAuth.createUserTag(name, color);
                        this.tags.push(tag);
                    } else {
                        tag = { id: Date.now(), ...tagData, sortOrder: this.tags.length, synced: false };
                        this.tags.push(tag);
                        localStorage.setItem('bible-tags', JSON.stringify(this.tags));
                    }
                } catch (err) {
                    console.error('Failed to create tag:', err);
                    return;
                }
            }

            // Check if verse already has a note with this tag — if so, remove it (toggle off)
            const existingNote = this.notes.find(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                (this.noteTags[n.id] || []).includes(tag.id)
            );
            if (existingNote) {
                await this.toggleNoteTag(existingNote.id, tag.id);
                // If the note has no content and no tags left, delete it
                const remainingTags = this.noteTags[existingNote.id] || [];
                if (!existingNote.content?.trim() && remainingTags.length === 0) {
                    await this.deleteNote(existingNote.id);
                }
                return;
            }

            // Check if verse already has a highlight note (no content) — add tag to it
            const emptyNote = this.notes.find(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                !n.content?.trim()
            );
            if (emptyNote) {
                // Clear existing tags on this empty note, apply new color
                const currentTagIds = this.noteTags[emptyNote.id] || [];
                for (const tid of currentTagIds) {
                    await this.toggleNoteTag(emptyNote.id, tid);
                }
                await this.toggleNoteTag(emptyNote.id, tag.id);
                return;
            }

            // Create a minimal note (empty content) with the tag
            const noteData = {
                book: this.currentBook,
                chapter: this.currentChapter,
                startVerse: verseNum,
                endVerse: verseNum,
                content: ''
            };
            try {
                let savedNoteId;
                if (this.authUser && window.SupabaseAuth) {
                    const savedNote = await window.SupabaseAuth.saveUserNote(noteData);
                    this.notes.unshift(savedNote);
                    savedNoteId = savedNote.id;
                } else {
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
                await this.toggleNoteTag(savedNoteId, tag.id);
            } catch (err) {
                console.error('Failed to create highlight:', err);
            }
        },

        async removeVerseHighlight(verseNum) {
            // Remove all tag-only (empty content) notes on this verse
            const toRemove = this.notes.filter(n =>
                n.book === this.currentBook &&
                n.chapter === this.currentChapter &&
                n.startVerse === verseNum &&
                (n.endVerse || n.startVerse) === verseNum &&
                !n.content?.trim()
            );
            for (const note of toRemove) {
                await this.deleteNote(note.id);
            }
            this.showHighlightPicker = null;
        },
};
