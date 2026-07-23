// bibleApp feature module: plans — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.plans = {
        // ========== READING PLAN METHODS ==========

        loadPlanProgress() {
            try {
                const saved = localStorage.getItem('readingPlanProgress');
                if (saved) {
                    this.planProgress = JSON.parse(saved);
                }
            } catch (err) {
                console.warn('Failed to load plan progress:', err);
            }
        },

        // Load plan progress from Supabase (called after auth is initialized)
        async loadPlanProgressFromSupabase() {
            if (!this.authUser || !window.SupabaseAuth?.fetchUserReadingPlans) return;

            try {
                // First, sync any local-only progress to Supabase
                await this.syncLocalPlanProgressToSupabase();

                // Fetch plans and progress from Supabase
                const plans = await window.SupabaseAuth.fetchUserReadingPlans();
                const progressData = await window.SupabaseAuth.fetchAllPlanProgress();

                // Merge with local data (Supabase takes precedence)
                for (const plan of plans) {
                    const progress = progressData[plan.planId];
                    this.planProgress[plan.planId] = {
                        startDate: plan.startDate,
                        completedDays: progress?.completedDays || [],
                        userPlanId: plan.id,
                        synced: true
                    };
                }

                this.planProgressSynced = true;
                this.savePlanProgress();
            } catch (err) {
                console.warn('Failed to load plan progress from Supabase:', err);
            }
        },

        // Sync local-only plan progress to Supabase
        async syncLocalPlanProgressToSupabase() {
            if (!this.authUser || !window.SupabaseAuth?.syncLocalPlanProgress) return;

            for (const [planId, data] of Object.entries(this.planProgress)) {
                // Skip if already synced
                if (data.userPlanId || data.synced) continue;

                if (data.startDate) {
                    try {
                        const result = await window.SupabaseAuth.syncLocalPlanProgress(
                            planId,
                            data.startDate,
                            data.completedDays || []
                        );
                        if (result.synced) {
                            this.planProgress[planId].userPlanId = result.userPlanId;
                            this.planProgress[planId].synced = true;
                        }
                    } catch (err) {
                        console.warn(`Failed to sync plan ${planId}:`, err);
                    }
                }
            }
        },

        savePlanProgress() {
            try {
                localStorage.setItem('readingPlanProgress', JSON.stringify(this.planProgress));
            } catch (err) {
                console.warn('Failed to save plan progress:', err);
            }
        },

        async openReadingPlan() {
            this.showReadingPlan = true;
            this.planLoading = true;

            try {
                // Load available plans
                const response = await fetch('/api/reading-plans');
                if (response.ok) {
                    const data = await response.json();
                    this.readingPlans = data.plans;

                    // If user has an active plan, load it
                    const activePlanId = Object.keys(this.planProgress).find(
                        id => this.planProgress[id].startDate
                    );

                    if (activePlanId) {
                        await this.loadPlan(activePlanId);
                    }
                }
            } catch (err) {
                console.error('Failed to load reading plans:', err);
                this.showToast('Failed to load reading plans', 'error');
            } finally {
                this.planLoading = false;
            }
        },

        async loadPlan(planId) {
            this.planLoading = true;
            try {
                const response = await fetch(`/api/reading-plans/${planId}`);
                if (response.ok) {
                    this.currentPlan = await response.json();

                    // Calculate current day based on start date
                    if (this.planProgress[planId]?.startDate) {
                        const today = this.getTodaysPlanDayForPlan(planId);
                        this.planDay = Math.max(1, Math.min(today || 1, this.currentPlan.duration_days));
                    } else {
                        this.planDay = 1;
                    }
                }
            } catch (err) {
                console.error('Failed to load plan:', err);
            } finally {
                this.planLoading = false;
            }
        },

        // Restore reading plan state from URL (used on page load and popstate)
        async restorePlanFromURL(planId, day) {
            try {
                // Load the plan data
                const response = await fetch(`/api/reading-plans/${planId}`);
                if (response.ok) {
                    this.currentPlan = await response.json();
                    this.planDay = Math.max(1, Math.min(day, this.currentPlan.duration_days));
                    // Start reading the plan
                    await this.startPlanReading();
                } else {
                    console.error('Plan not found:', planId);
                    // Fallback to home
                    window.history.replaceState({}, '', '/');
                }
            } catch (err) {
                console.error('Failed to restore plan from URL:', err);
                window.history.replaceState({}, '', '/');
            }
        },

        // Show start date picker before starting plan
        planStartDate: '',  // For the date picker input
        showPlanStartPicker: false,
        showCatchUpPrompt: false,  // For the catch-up confirmation
        pendingPlanId: null,

        promptStartPlan(planId) {
            // Default to Jan 1 of current year for annual plans
            const year = new Date().getFullYear();
            this.planStartDate = `${year}-01-01`;
            this.pendingPlanId = planId;
            this.showPlanStartPicker = true;
        },

        async confirmStartPlan() {
            if (!this.pendingPlanId || !this.planStartDate) return;
            await this.startPlan(this.pendingPlanId, this.planStartDate);
            this.showPlanStartPicker = false;
            this.pendingPlanId = null;
        },

        cancelStartPlan() {
            this.showPlanStartPicker = false;
            this.showCatchUpPrompt = false;
            this.pendingPlanId = null;
        },

        selectJanuaryFirst() {
            this.planStartDate = new Date().getFullYear() + '-01-01';
            this.checkForCatchUp();
        },

        checkForCatchUp() {
            if (!this.planStartDate) return;

            const startDate = new Date(this.planStartDate + 'T00:00:00');
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            // ponytail: Math.round not Math.floor — DST spring-forward loses 1h, floor truncates to wrong day
            const daysDiff = Math.round((today - startDate) / (1000 * 60 * 60 * 24));

            // If the start date is in the past (more than 0 days ago), show catch-up prompt
            if (daysDiff > 0) {
                this.showCatchUpPrompt = true;
            } else {
                // Start date is today or in the future, just proceed
                this.confirmStartPlan();
            }
        },

        getDaysElapsed() {
            if (!this.planStartDate) return 0;
            const startDate = new Date(this.planStartDate + 'T00:00:00');
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            return Math.round((today - startDate) / (1000 * 60 * 60 * 24));
        },

        formatStartDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
        },

        async confirmStartPlanWithCatchUp(shouldCatchUp) {
            if (!this.pendingPlanId || !this.planStartDate) return;

            const daysElapsed = this.getDaysElapsed();
            const catchUpDays = shouldCatchUp && daysElapsed > 0
                ? Array.from({ length: daysElapsed }, (_, i) => i + 1)
                : [];

            await this.startPlan(this.pendingPlanId, this.planStartDate, catchUpDays);
            this.showPlanStartPicker = false;
            this.showCatchUpPrompt = false;
            this.pendingPlanId = null;
        },

        // Core plan-start: write progress, sync to Supabase, save, load the plan.
        // catchUpDays marks past days complete (from the catch-up prompt).
        async startPlan(planId, startDate = null, catchUpDays = []) {
            if (!startDate) {
                // Default: start with today
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                startDate = today.toISOString().split('T')[0];
            }

            this.planProgress[planId] = {
                startDate: startDate,
                completedDays: []
            };

            // Sync to Supabase if logged in
            if (this.authUser && window.SupabaseAuth?.subscribeToReadingPlan) {
                try {
                    const result = await window.SupabaseAuth.subscribeToReadingPlan(planId, startDate);
                    this.planProgress[planId].userPlanId = result.id;
                    this.planProgress[planId].synced = true;
                } catch (err) {
                    console.warn('Failed to sync plan to Supabase:', err);
                }
            }

            // Mark catch-up days complete
            if (catchUpDays.length > 0) {
                this.planProgress[planId].completedDays = [...catchUpDays];

                // Bulk sync to Supabase if logged in
                const userPlanId = this.planProgress[planId].userPlanId;
                if (this.authUser && userPlanId && window.SupabaseAuth?.bulkMarkDaysComplete) {
                    try {
                        await window.SupabaseAuth.bulkMarkDaysComplete(userPlanId, catchUpDays);
                    } catch (err) {
                        console.warn('Failed to bulk sync catch-up days to Supabase:', err);
                    }
                }
            }

            this.savePlanProgress();
            this.loadPlan(planId);
        },

        async resetPlan(planId) {
            if (confirm('Reset this plan? All progress will be lost.')) {
                // Unsubscribe from Supabase if logged in
                if (this.authUser && window.SupabaseAuth?.unsubscribeFromReadingPlan) {
                    try {
                        await window.SupabaseAuth.unsubscribeFromReadingPlan(planId);
                    } catch (err) {
                        console.warn('Failed to unsubscribe from plan in Supabase:', err);
                    }
                }

                delete this.planProgress[planId];
                this.savePlanProgress();
                this.currentPlan = null;
                this.planDay = 1;
            }
        },

        getTodaysPlanDayForPlan(planId) {
            if (!this.planProgress[planId]?.startDate) return null;

            // Append T00:00:00 to ensure local timezone parsing (not UTC)
            const dateStr = this.planProgress[planId].startDate;
            const startDate = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
            const today = new Date();
            startDate.setHours(0, 0, 0, 0);
            today.setHours(0, 0, 0, 0);
            const daysDiff = Math.round((today - startDate) / (1000 * 60 * 60 * 24)) + 1;
            return Math.max(1, Math.min(daysDiff, 365));
        },

        getPlanDayReadings(day) {
            if (!this.currentPlan) return null;
            return this.currentPlan.days.find(d => d.day === day);
        },

        isDayCompleted(day) {
            if (!this.currentPlan) return false;
            const planId = this.currentPlan.id;
            return this.planProgress[planId]?.completedDays?.includes(day) || false;
        },

        async toggleDayComplete(day) {
            if (!this.currentPlan) return;
            const planId = this.currentPlan.id;

            if (!this.planProgress[planId]) {
                this.planProgress[planId] = { completedDays: [] };
            }
            if (!this.planProgress[planId].completedDays) {
                this.planProgress[planId].completedDays = [];
            }

            const idx = this.planProgress[planId].completedDays.indexOf(day);
            const isCompleting = idx === -1;

            if (isCompleting) {
                this.planProgress[planId].completedDays.push(day);
            } else {
                this.planProgress[planId].completedDays.splice(idx, 1);
            }
            this.savePlanProgress();

            // Sync to Supabase if logged in
            const userPlanId = this.planProgress[planId].userPlanId;
            if (this.authUser && userPlanId && window.SupabaseAuth) {
                try {
                    if (isCompleting) {
                        await window.SupabaseAuth.markDayComplete(userPlanId, day);
                    } else {
                        await window.SupabaseAuth.unmarkDayComplete(userPlanId, day);
                    }
                } catch (err) {
                    console.warn('Failed to sync day completion to Supabase:', err);
                }
            }
        },

        async markAllUpToToday() {
            if (!this.currentPlan) return;
            const planId = this.currentPlan.id;
            const today = this.getTodaysPlanDay(planId);
            if (!today) return;

            if (!this.planProgress[planId]) {
                this.planProgress[planId] = { completedDays: [] };
            }
            if (!this.planProgress[planId].completedDays) {
                this.planProgress[planId].completedDays = [];
            }

            const newDays = [];
            for (let i = 1; i <= today; i++) {
                if (!this.planProgress[planId].completedDays.includes(i)) {
                    this.planProgress[planId].completedDays.push(i);
                    newDays.push(i);
                }
            }
            this.savePlanProgress();

            const userPlanId = this.planProgress[planId].userPlanId;
            if (this.authUser && userPlanId && window.SupabaseAuth?.bulkMarkDaysComplete && newDays.length) {
                try {
                    await window.SupabaseAuth.bulkMarkDaysComplete(userPlanId, newDays);
                } catch (err) {
                    console.warn('Failed to sync bulk completion to Supabase:', err);
                }
            }
        },

        getCompletedDaysCount() {
            if (!this.currentPlan) return 0;
            const planId = this.currentPlan.id;
            return this.planProgress[planId]?.completedDays?.length || 0;
        },

        getPlanProgressPercent() {
            if (!this.currentPlan) return 0;
            const completed = this.getCompletedDaysCount();
            return Math.round((completed / this.currentPlan.duration_days) * 100);
        },

        isPlanComplete() {
            if (!this.currentPlan) return false;
            return this.getCompletedDaysCount() >= this.currentPlan.duration_days;
        },

        goToPlanDay(day) {
            this.planDay = Math.max(1, Math.min(day, this.currentPlan?.duration_days || 365));
        },

        goToTodaysPlanDay() {
            if (!this.currentPlan) return;
            const today = this.getTodaysPlanDayForPlan(this.currentPlan.id);
            if (today) {
                this.planDay = today;
            }
        },

        // Normalize a full reference (book + chapter/verse)
        normalizeReference(ref) {
            // Match book name at the start (including numbered books like "1 Chron.")
            const match = ref.match(/^(\d?\s*[A-Za-z][A-Za-z.\s]*?)(\s+\d.*)$/);
            if (match) {
                const book = normalizeBookName(match[1].trim());
                return book + match[2];
            }
            return ref;
        },

        // Parse a reading reference that might be a chapter range (e.g., "Genesis 1-3")
        // or semicolon-separated references (e.g., "2 Samuel 5; 1 Chron. 11-12")
        parseReadingReference(ref) {
            // First, split on semicolons for multiple separate references
            if (ref.includes(';')) {
                const parts = ref.split(';').map(p => p.trim()).filter(p => p);
                let allRefs = [];
                for (const part of parts) {
                    allRefs = allRefs.concat(this.parseReadingReference(part));
                }
                return allRefs;
            }

            // Normalize the reference (handles abbreviations like "1 Chron." -> "1 Chronicles")
            ref = this.normalizeReference(ref);

            // Match chapter ranges like "Genesis 1-3" or "Job 1-3"
            // Must NOT have a colon (which would indicate verse range like "Psalm 17:1-15")
            const chapterRangeMatch = ref.match(/^([A-Za-z0-9\s]+?)\s+(\d+)-(\d+)$/);
            if (chapterRangeMatch && !ref.includes(':')) {
                const book = chapterRangeMatch[1].trim();
                const startChapter = parseInt(chapterRangeMatch[2]);
                const endChapter = parseInt(chapterRangeMatch[3]);
                const chapters = [];
                for (let ch = startChapter; ch <= endChapter; ch++) {
                    chapters.push(`${book} ${ch}`);
                }
                return chapters;
            }
            // Single chapter, verse reference, or verse range - pass through as-is
            return [ref];
        },

        // Load all passages for the day into the main reader view
        async startPlanReading() {
            if (!this.currentPlan) return;

            const readings = this.getPlanDayReadings(this.planDay);
            if (!readings) return;

            // Plan loading is a navigation — invalidate stale loaders (B4)
            const gen = ++this._loadGeneration;

            this.showReadingPlan = false;
            this.loading = true;
            this.combinedPlanReading = true;
            this.planReadingSections = [];
            this.planReadingChapters = [];

            // We'll load verses into the main this.verses array
            let allVerses = [];
            let allCrossRefs = [];
            let allCommentary = [];
            let chaptersToLoadCommentary = [];

            // Parse and load each reading
            const readingTypes = ['chronological', 'psalms', 'proverbs'];

            // P4: fire all passage fetches concurrently, then assemble results
            // in the original section/chapter order.
            const sectionPlans = [];
            for (const type of readingTypes) {
                const ref = readings[type];
                if (!ref) continue;

                // Parse the reference - might be multiple chapters
                const refs = this.parseReadingReference(ref);
                const label = type === 'chronological' ? 'Main Reading' : type.charAt(0).toUpperCase() + type.slice(1);

                sectionPlans.push({
                    type, label, reference: ref,
                    fetches: refs.map(singleRef =>
                        fetch(`/api/passage/${encodeURIComponent(singleRef)}?translation=${this.translation}`)
                            .then(response => response.ok ? response.json() : null)
                            .then(data => ({ singleRef, data }))
                            .catch(err => {
                                console.error(`Failed to load ${type} (${singleRef}):`, err);
                                return { singleRef, data: null };
                            })
                    )
                });
            }

            for (const section of sectionPlans) {
                const { type, label } = section;

                // Track the section start
                const sectionStartIndex = allVerses.length;

                try {
                    let isFirstChapterInSection = true;
                    const results = await Promise.all(section.fetches);
                    for (const { singleRef, data } of results) {
                        if (data) {

                            // Collect cross-references with book/chapter context
                            if (data.cross_references && data.cross_references.length > 0) {
                                const crossRefsWithContext = data.cross_references.map(cr => ({
                                    ...cr,
                                    _sourceRef: singleRef,
                                    _sourceBook: data.reference.replace(/\s+\d+.*$/, ''),
                                    _sourceChapter: parseInt(data.reference.match(/\s+(\d+)/)?.[1] || 1)
                                }));
                                allCrossRefs = allCrossRefs.concat(crossRefsWithContext);
                            }

                            // Track chapters for commentary loading and notes filtering
                            const bookMatch = data.reference.match(/^(.+?)\s+(\d+)/);
                            if (bookMatch) {
                                const chapterInfo = {
                                    book: bookMatch[1],
                                    chapter: parseInt(bookMatch[2]),
                                    ref: `${bookMatch[1]} ${bookMatch[2]}`
                                };
                                chaptersToLoadCommentary.push(chapterInfo);
                                // Also track for notes panel (deduplicated later)
                                this.planReadingChapters.push({
                                    book: chapterInfo.book,
                                    chapter: chapterInfo.chapter
                                });
                            }

                            // Filter verses to only highlighted ones if a verse range was requested
                            let verses = data.verses;
                            if (data.highlighted_verses && data.highlighted_verses.length > 0 &&
                                data.highlighted_verses.length < data.verses.length) {
                                // Filter to only the highlighted/requested verses
                                const highlightedSet = new Set(data.highlighted_verses);
                                verses = data.verses.filter(v => highlightedSet.has(v.verse));
                            }

                            // Add book/chapter context to ALL verses for note-taking
                            // bookMatch already declared above at line 3005
                            const verseBook = bookMatch ? bookMatch[1] : 'Unknown';
                            const verseChapter = bookMatch ? parseInt(bookMatch[2]) : 1;

                            verses = verses.map((v, idx) => ({
                                ...v,
                                html: this.formatVerseText(v.text),  // precomputed render (P5)
                                _book: verseBook,
                                _chapter: verseChapter,
                                // Mark first verse of each chapter for section headers
                                _chapterStart: idx === 0,
                                _chapterRef: idx === 0 ? singleRef : null,
                                _sectionType: idx === 0 ? type : null,
                                _sectionLabel: idx === 0 && isFirstChapterInSection ? label : null
                            }));
                            if (verses.length > 0) {
                                isFirstChapterInSection = false;
                            }
                            allVerses = allVerses.concat(verses);
                        }
                    }

                    // Add section info for the header bar
                    this.planReadingSections.push({
                        type,
                        label,
                        reference: section.reference,
                        startIndex: sectionStartIndex
                    });
                } catch (err) {
                    console.error(`Failed to load ${type}:`, err);
                }
            }

            // Bail if the user navigated away while the plan was loading (B4)
            if (gen !== this._loadGeneration) return;

            // Set combined verses in the main reader
            this.verses = allVerses;
            this.currentReference = `${this.currentPlan.name} - Day ${this.planDay}`;
            this.highlightedVerses = [];
            this.crossRefs = allCrossRefs;
            this.combinedCrossRefs = allCrossRefs;  // Store for restoration after verse deselect
            this.commentary = [];
            this.loading = false;
            this.rebuildVerseColorMap();

            // Clear book/chapter since we're in combined mode
            this.currentBook = null;
            this.currentChapter = null;

            // P4: load commentary and interlinear for all chapters (deduplicated)
            // concurrently — one round-trip of wall clock instead of 2×chapters.
            const uniqueChapters = [...new Map(chaptersToLoadCommentary.map(c => [c.ref, c])).values()];

            const commentaryPromise = Promise.all(uniqueChapters.map(chapterInfo =>
                fetch(`/api/passage/${encodeURIComponent(chapterInfo.ref)}/commentary`)
                    .then(resp => resp.ok ? resp.json() : null)
                    .then(commentaryData => {
                        if (!commentaryData?.entries?.length) return [];
                        // Add book/chapter context to each entry
                        return commentaryData.entries.map(entry => ({
                            ...entry,
                            _sourceBook: chapterInfo.book,
                            _sourceChapter: chapterInfo.chapter,
                            _sourceRef: chapterInfo.ref
                        }));
                    })
                    .catch(err => {
                        console.error(`Failed to load commentary for ${chapterInfo.ref}:`, err);
                        return [];
                    })
            ));

            const interlinearPromise = Promise.all(uniqueChapters.map(chapterInfo =>
                fetch(`/api/passage/${encodeURIComponent(chapterInfo.ref)}/interlinear?translation=${this.translation}`)
                    .then(resp => resp.ok ? resp.json() : null)
                    .then(data => ({ chapterInfo, data }))
                    .catch(err => {
                        console.error(`Failed to load interlinear for ${chapterInfo.ref}:`, err);
                        return { chapterInfo, data: null };
                    })
            ));

            this.interlinearData = {};
            const [commentaryGroups, interlinearResults] = await Promise.all([commentaryPromise, interlinearPromise]);

            // User navigated away mid-load — do not clobber their state (B4)
            if (gen !== this._loadGeneration) return;

            for (const entries of commentaryGroups) {
                allCommentary = allCommentary.concat(entries);
            }
            this.commentary = allCommentary;
            this.combinedCommentary = allCommentary;  // Store for restoration after verse deselect

            const interlinearMap = {};
            for (const { chapterInfo, data } of interlinearResults) {
                if (data?.has_interlinear && data.verses) {
                    // Store with compound key: book|chapter|verse
                    for (const [verseNum, words] of Object.entries(data.verses)) {
                        interlinearMap[`${chapterInfo.book}|${chapterInfo.chapter}|${verseNum}`] = {
                            language: data.language,
                            words: words
                        };
                    }
                }
            }
            this.interlinearData = interlinearMap;

            // Setup scroll-based verse tracking
            this.$nextTick(() => {
                this.observeVerses();
            });

            // Update URL to reflect plan reading state
            this.updateURL();
        },

        exitPlanReadingMode() {
            this.planReadingMode = false;
            this.combinedPlanReading = false;
            this.wasInPlanReading = false;
            this.planReadings = [];
            this.planReadingSections = [];
            this.planReadingChapters = [];
            // Go back to plan view if a plan is active, otherwise load Genesis 1
            if (this.currentPlan) {
                this.showReadingPlan = true;
            } else {
                this.referenceInput = 'Genesis 1';
                this.loadPassage();
            }
        },

        // Return to plan reading after navigating away (e.g., clicking a cross-ref)
        returnToPlanReading() {
            this.wasInPlanReading = false;
            this.startPlanReading();
        },

        markPlanDayAndContinue() {
            if (!this.isDayCompleted(this.planDay)) {
                this.toggleDayComplete(this.planDay);
            }

            // Move to next day or show completion
            if (this.planDay < (this.currentPlan?.duration_days || 365)) {
                this.planDay++;
                this.startPlanReading();
            } else {
                this.exitPlanReadingMode();
                this.showToast('Plan complete! Congratulations!', 'success');
            }
        },

        // Navigate to a specific passage from the plan (opens in reader)
        goToPlanPassage(ref) {
            this.showReadingPlan = false;
            this.planReadingMode = false;
            this.referenceInput = ref;
            this.loadPassage();
        },

        formatPlanDate(planId) {
            if (!this.planProgress[planId]?.startDate) return '';
            const dateStr = this.planProgress[planId].startDate;
            const date = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        },

        getPlanDayDate(day) {
            const planId = this.currentPlan?.id;
            if (!planId || !this.planProgress[planId]?.startDate) return '';
            const dateStr = this.planProgress[planId].startDate;
            const start = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
            start.setDate(start.getDate() + (day - 1));
            return start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        },
};
