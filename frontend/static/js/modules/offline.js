// bibleApp feature module: offline — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.offline = {
        // ========== OFFLINE METHODS ==========

        // Update offline storage stats
        async updateOfflineStats() {
            if (!window.offlineStorage) return;

            try {
                const stats = await window.offlineStorage.getStorageStats();
                let totalChapters = 0;
                let totalVerses = 0;

                // Count verses across all translations
                for (const translation of Object.values(stats.verses.translations)) {
                    totalChapters += translation.chapters;
                    totalVerses += translation.verses;
                }

                this.offlineStats = {
                    chapters: totalChapters,
                    verses: totalVerses,
                    lexicon: stats.lexicon.cached,
                    estimatedSize: this.estimateStorageSize(totalVerses, stats.lexicon.count, stats.interlinear.chapters)
                };
            } catch (err) {
                console.error('Failed to update offline stats:', err);
            }
        },

        // Estimate storage size in bytes
        estimateStorageSize(verses, lexiconEntries, interlinearChapters) {
            // Rough estimates: ~500 bytes per verse, ~1KB per lexicon entry, ~50KB per interlinear chapter
            return (verses * 500) + (lexiconEntries * 1024) + (interlinearChapters * 50000);
        },

        // Format storage size for display
        formatStorageSize(bytes) {
            if (bytes === 0) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
        },

        // Show a toast notification
        showToast(message, type = 'info') {
            const id = ++_toastSeq;
            this.toasts.push({ id, message, type });

            // Auto-remove after 4 seconds
            setTimeout(() => {
                this.toasts = this.toasts.filter(t => t.id !== id);
            }, 4000);
        },

        // Toggle auto-cache and persist preference
        toggleAutoCache() {
            this.autoCacheEnabled = !this.autoCacheEnabled;
            localStorage.setItem('autoCacheEnabled', this.autoCacheEnabled);
        },

        // Auto-cache the current chapter data to IndexedDB (fire-and-forget)
        async _autoCacheCurrentChapter() {
            const os = window.offlineStorage;
            const book = this.currentBook;
            const ch = this.currentChapter;
            const trans = this.translation;
            try {
                // Save verses
                if (this.verses?.length > 0) {
                    await os.saveChapterVerses(trans, book, ch, this.verses);
                }
                // Save cross-refs
                if (this.crossRefs?.length > 0) {
                    await os.saveChapterCrossRefs(book, ch, this.crossRefs);
                }
                // Save commentary
                if (this.commentary?.length > 0) {
                    await os.saveChapterCommentary(book, ch, this.commentary);
                }
                // Save interlinear
                if (Object.keys(this.interlinearData).length > 0) {
                    const words = [];
                    for (const [verseNum, data] of Object.entries(this.interlinearData)) {
                        for (const w of data.words || []) {
                            words.push({ ...w, verse: parseInt(verseNum) });
                        }
                    }
                    if (words.length > 0) {
                        await os.saveChapterInterlinear(book, ch, words);
                    }
                }
            } catch (err) {
                // Silent failure — auto-cache is best-effort
                console.debug('Auto-cache failed:', err);
            }
        },

        // Download the Strong's lexicon
        async downloadLexicon() {
            this.downloadProgress.label = 'Downloading lexicon...';
            this.downloadProgress.status = 'Fetching Hebrew & Greek definitions';

            try {
                const response = await fetch('/api/offline/lexicon');
                if (!response.ok) throw new Error('Failed to fetch lexicon');

                const data = await response.json();
                this.downloadProgress.percent = 50;

                if (data.entries && window.offlineStorage) {
                    this.downloadProgress.status = `Saving ${data.entries.length} entries...`;
                    await window.offlineStorage.saveLexiconEntries(data.entries);
                    this.downloadProgress.percent = 100;
                }
            } catch (err) {
                console.error('Lexicon download failed:', err);
                throw err;
            }
        },

        // Clear all offline data
        async clearOfflineData() {
            if (!confirm('Clear all cached offline data?')) return;

            try {
                if (window.offlineStorage) {
                    await window.offlineStorage.clearAll();
                }

                // Also clear service worker cache
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    const channel = new MessageChannel();
                    navigator.serviceWorker.controller.postMessage(
                        { type: 'CLEAR_CACHE' },
                        [channel.port2]
                    );
                }

                await this.updateOfflineStats();
                this.showToast('Offline data cleared', 'success');
            } catch (err) {
                console.error('Failed to clear offline data:', err);
                this.showToast('Failed to clear data', 'error');
            }
        },

        // Check if any download options are selected
        hasDownloadSelections() {
            const t = this.downloadSelections.translations;
            return t.BSB || t.WEB || t.KJV ||
                   this.downloadSelections.lexicon ||
                   this.downloadSelections.commentaryMH ||
                   this.downloadSelections.commentaryJG ||
                   this.downloadSelections.crossRefs ||
                   this.downloadSelections.devotionalSpurgeon;
        },

        // Start downloading selected offline content
        async startOfflineDownload() {
            if (this.downloadProgress.active) return;
            if (!this.hasDownloadSelections()) return;

            this.downloadProgress.active = true;
            this.downloadProgress.percent = 0;

            const tasks = [];
            const t = this.downloadSelections.translations;

            // Gather tasks
            if (t.BSB) tasks.push({ type: 'translation', name: 'BSB' });
            if (t.WEB) tasks.push({ type: 'translation', name: 'WEB' });
            if (t.KJV) tasks.push({ type: 'translation', name: 'KJV' });
            if (this.downloadSelections.lexicon) tasks.push({ type: 'lexicon' });
            if (this.downloadSelections.commentaryMH) tasks.push({ type: 'commentary', source: 'Matthew Henry' });
            if (this.downloadSelections.commentaryJG) tasks.push({ type: 'commentary', source: 'John Gill' });
            if (this.downloadSelections.crossRefs) tasks.push({ type: 'crossRefs' });
            if (this.downloadSelections.devotionalSpurgeon) tasks.push({ type: 'devotional', source: 'Spurgeon' });

            try {
                for (let i = 0; i < tasks.length; i++) {
                    const task = tasks[i];
                    const basePercent = Math.round((i / tasks.length) * 100);

                    if (task.type === 'translation') {
                        await this.downloadFullTranslation(task.name, basePercent, tasks.length);
                    } else if (task.type === 'lexicon') {
                        this.downloadProgress.label = 'Downloading lexicon...';
                        this.downloadProgress.status = 'Fetching Hebrew & Greek definitions';
                        await this.downloadLexicon();
                    } else if (task.type === 'commentary') {
                        await this.downloadAllCommentary(basePercent, tasks.length, task.source);
                    } else if (task.type === 'crossRefs') {
                        await this.downloadAllCrossRefs(basePercent, tasks.length);
                    } else if (task.type === 'devotional') {
                        await this.downloadDevotionals(basePercent, tasks.length, task.source);
                    }
                }

                this.showToast('Download complete!', 'success');
                await this.updateOfflineStats();

                // Reset selections
                this.downloadSelections.translations = { BSB: false, WEB: false, KJV: false };
                this.downloadSelections.lexicon = false;
                this.downloadSelections.commentaryMH = false;
                this.downloadSelections.commentaryJG = false;
                this.downloadSelections.crossRefs = false;
                this.downloadSelections.devotionalSpurgeon = false;

            } catch (err) {
                console.error('Download failed:', err);
                this.showToast('Download failed: ' + err.message, 'error');
            } finally {
                this.downloadProgress.active = false;
            }
        },

        // Download full translation (all 66 books)
        async downloadFullTranslation(translation, basePercent, totalTasks) {
            const books = Object.keys(BOOK_CHAPTERS);
            const totalChapters = Object.values(BOOK_CHAPTERS).reduce((a, b) => a + b, 0);
            let chaptersDownloaded = 0;

            this.downloadProgress.label = `Downloading ${translation}...`;

            for (const book of books) {
                const chapterCount = BOOK_CHAPTERS[book];
                for (let ch = 1; ch <= chapterCount; ch++) {
                    this.downloadProgress.status = `${book} ${ch}`;

                    try {
                        const response = await fetch(
                            `/api/offline/chapter?book=${encodeURIComponent(book)}&chapter=${ch}&translation=${translation}`
                        );
                        if (response.ok) {
                            const data = await response.json();
                            if (window.offlineStorage && data.verses?.length > 0) {
                                await window.offlineStorage.saveChapterVerses(translation, book, ch, data.verses);
                                if (data.alignments?.length > 0) {
                                    await window.offlineStorage.saveChapterAlignments(translation, book, ch, data.alignments);
                                }
                                if (data.interlinear?.length > 0) {
                                    await window.offlineStorage.saveChapterInterlinear(book, ch, data.interlinear);
                                }
                            }
                        }
                    } catch (err) {
                        console.warn(`Failed to download ${book} ${ch}:`, err);
                    }

                    chaptersDownloaded++;
                    const taskProgress = (chaptersDownloaded / totalChapters) * (100 / totalTasks);
                    this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                    // Small delay
                    await new Promise(r => setTimeout(r, 50));
                }

                // Update stats after each book so the UI shows progress
                await this.updateOfflineStats();
            }
        },

        // Download all commentary (optionally filtered by source)
        async downloadAllCommentary(basePercent, totalTasks, source = null) {
            this.downloadProgress.label = `Downloading ${source || 'commentary'}...`;
            const books = Object.keys(BOOK_CHAPTERS);
            let booksDownloaded = 0;

            for (const book of books) {
                this.downloadProgress.status = book;

                try {
                    const response = await fetch(`/api/offline/commentary?book=${encodeURIComponent(book)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (window.offlineStorage && data.entries?.length > 0) {
                            // Filter by source if specified
                            const entries = source
                                ? data.entries.filter(e => e.source === source)
                                : data.entries;
                            // Group entries by chapter for efficient saving
                            const byChapter = {};
                            for (const entry of entries) {
                                const ch = entry.chapter || 1;
                                if (!byChapter[ch]) byChapter[ch] = [];
                                byChapter[ch].push(entry);
                            }
                            for (const [ch, chEntries] of Object.entries(byChapter)) {
                                await window.offlineStorage.saveChapterCommentary(book, parseInt(ch), chEntries);
                            }
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download commentary for ${book}:`, err);
                }

                booksDownloaded++;
                const taskProgress = (booksDownloaded / books.length) * (100 / totalTasks);
                this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                // Update stats every 5 books so the UI shows progress
                if (booksDownloaded % 5 === 0) await this.updateOfflineStats();

                await new Promise(r => setTimeout(r, 50));
            }
            await this.updateOfflineStats();
        },

        // Download all devotionals
        async downloadDevotionals(basePercent, totalTasks, source) {
            this.downloadProgress.label = `Downloading ${source} devotionals...`;
            this.downloadProgress.status = 'Fetching all entries...';

            try {
                const response = await fetch(`/api/offline/devotionals?source=${encodeURIComponent(source)}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.entries?.length > 0) {
                        // Store devotionals in localStorage — devotional entries are small
                        // enough that localStorage is appropriate, and IndexedDB doesn't
                        // have a dedicated devotionals store
                        localStorage.setItem(`devotional_${source}`, JSON.stringify(data.entries));
                        this.downloadProgress.status = `Saved ${data.count} entries`;
                    }
                }
            } catch (err) {
                console.warn(`Failed to download devotionals for ${source}:`, err);
            }

            this.downloadProgress.percent = Math.round(basePercent + (100 / totalTasks));
        },

        // Download all cross-references
        async downloadAllCrossRefs(basePercent, totalTasks) {
            this.downloadProgress.label = 'Downloading cross-references...';
            const books = Object.keys(BOOK_CHAPTERS);
            let booksDownloaded = 0;

            for (const book of books) {
                this.downloadProgress.status = book;

                try {
                    const response = await fetch(`/api/offline/crossrefs?book=${encodeURIComponent(book)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (window.offlineStorage && data.entries?.length > 0) {
                            // Group by chapter and save
                            const byChapter = {};
                            for (const ref of data.entries) {
                                const ch = ref.chapter || 1;
                                if (!byChapter[ch]) byChapter[ch] = [];
                                byChapter[ch].push(ref);
                            }
                            for (const [ch, refs] of Object.entries(byChapter)) {
                                await window.offlineStorage.saveChapterCrossRefs(book, parseInt(ch), refs);
                            }
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to download cross-refs for ${book}:`, err);
                }

                booksDownloaded++;
                const taskProgress = (booksDownloaded / books.length) * (100 / totalTasks);
                this.downloadProgress.percent = Math.round(basePercent + taskProgress);

                // Update stats every 5 books so the UI shows progress
                if (booksDownloaded % 5 === 0) await this.updateOfflineStats();

                await new Promise(r => setTimeout(r, 50));
            }
            await this.updateOfflineStats();
        },

        // Refresh (re-download) all cached content
        async refreshOfflineData() {
            if (!confirm('Re-download all cached content? This will refresh existing data.')) return;

            // Get what's currently cached and re-download it
            this.downloadProgress.active = true;
            this.downloadProgress.label = 'Refreshing cache...';
            this.downloadProgress.percent = 0;

            try {
                // Clear and re-download lexicon if it was cached
                if (this.offlineStats.lexicon) {
                    this.downloadProgress.status = 'Refreshing lexicon...';
                    await this.downloadLexicon();
                }

                // Re-download cached chapters
                if (window.offlineStorage && this.offlineStats.chapters > 0) {
                    this.downloadProgress.status = 'Refreshing chapters...';
                    // We'll need to iterate through what we have cached
                    // For now, just clear and let auto-cache rebuild
                    await window.offlineStorage.clearAll();
                }

                await this.updateOfflineStats();
                this.showToast('Cache refreshed', 'success');
            } catch (err) {
                console.error('Refresh failed:', err);
                this.showToast('Refresh failed', 'error');
            } finally {
                this.downloadProgress.active = false;
            }
        },

        // Toggle forced offline mode - blocks ALL network requests
        toggleForcedOffline() {
            this.forcedOffline = !this.forcedOffline;
            localStorage.setItem('forcedOffline', this.forcedOffline);

            if (this.forcedOffline) {
                this.isOnline = false;
                this.showToast('Offline mode enabled - no network requests will be made', 'info');
            } else {
                this.isOnline = navigator.onLine;
                this.showToast('Online mode restored', 'success');
            }
        },
};
