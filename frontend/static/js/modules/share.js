// bibleApp feature module: share — merged via Object.assign in app.js
window.BibleModules = window.BibleModules || {};
window.BibleModules.share = {
        // ========== Share Jesus Functions ==========

        // Start Share Jesus verse presentation
        startShareJesusVerses() {
            this.showShareJesus = false;
            this.openSingleVerseView(this.shareJesusVerses, {
                prompt: 'Have them read aloud, then ask: "What does this say to you?"',
                onFinish: () => { this.showShareJesus = true; }
            });
        },

        // Open Today's Reading
        openTodaysReading() {
            this.showSideMenu = false;
            // If we have an active plan, go directly to today's reading
            if (this.currentPlan) {
                const today = this.getTodaysPlanDay();
                if (today) {
                    this.planDay = today;
                    this.startPlanReading();
                } else {
                    // Fallback to opening the reading plan modal
                    this.openReadingPlan();
                }
            } else {
                // No active plan - open the reading plan picker
                this.openReadingPlan();
            }
        },

        // Get today's day number in the current plan (wrapper for side menu)
        getTodaysPlanDay() {
            if (!this.currentPlan) return null;
            // Use the existing function that takes planId
            return this.getTodaysPlanDayForPlan(this.currentPlan.id);
        },


        // ========== VERSE SHARING METHODS ==========

        shareBackgrounds: [
            { name: 'Sunset', colors: ['#667eea', '#764ba2'] },
            { name: 'Ocean', colors: ['#2193b0', '#6dd5ed'] },
            { name: 'Dark', colors: ['#1a1a2e', '#16213e'] },
            { name: 'Light', colors: ['#f5f7fa', '#c3cfe2'] },
        ],

        toggleShareMode() {
            this.shareMode = !this.shareMode;
            this.shareSelectedVerses = [];
        },

        toggleShareVerse(verseNum) {
            const idx = this.shareSelectedVerses.indexOf(verseNum);
            if (idx > -1) this.shareSelectedVerses.splice(idx, 1);
            else this.shareSelectedVerses.push(verseNum);
            this.shareSelectedVerses.sort((a, b) => a - b);
        },

        getShareVerseText() {
            if (this.shareSelectedVerses.length === 0) return '';
            return this.shareSelectedVerses.map(vn => {
                const verse = this.verses.find(v => v.verse === vn);
                return verse ? verse.text : '';
            }).filter(Boolean).join(' ');
        },

        getShareReference() {
            if (this.shareSelectedVerses.length === 0) return '';
            const first = this.shareSelectedVerses[0];
            const last = this.shareSelectedVerses[this.shareSelectedVerses.length - 1];
            if (first === last) {
                return `${this.currentBook} ${this.currentChapter}:${first}`;
            }
            return `${this.currentBook} ${this.currentChapter}:${first}-${last}`;
        },

        getShareLink() {
            if (this.shareSelectedVerses.length === 0) return '';
            const first = this.shareSelectedVerses[0];
            const last = this.shareSelectedVerses[this.shareSelectedVerses.length - 1];
            const bookPath = this.currentBook.replace(/\s+/g, '-');
            if (first === last) {
                return `${window.location.origin}/${bookPath}/${this.currentChapter}/${first}`;
            }
            return `${window.location.origin}/${bookPath}/${this.currentChapter}/${first}-${last}`;
        },

        openShareModal() {
            if (this.shareSelectedVerses.length === 0) return;
            this.showShareModal = true;
            this.shareImagePreview = null;
            this.$nextTick(() => this.generateVerseImagePreview());
        },

        async copyShareText() {
            const text = `"${this.getShareVerseText()}" — ${this.getShareReference()} (${this.translation})`;
            try {
                await navigator.clipboard.writeText(text);
                this.showToast('Verse text copied', 'success');
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        },

        async copyShareLink() {
            try {
                await navigator.clipboard.writeText(this.getShareLink());
                this.showToast('Link copied', 'success');
            } catch (err) {
                console.error('Failed to copy link:', err);
            }
        },

        async nativeShare() {
            if (!navigator.share) return;
            try {
                await navigator.share({
                    title: this.getShareReference(),
                    text: `"${this.getShareVerseText()}" — ${this.getShareReference()}`,
                    url: this.getShareLink()
                });
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Share failed:', err);
                }
            }
        },

        generateVerseImagePreview() {
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const bg = this.shareBackgrounds[this.shareBackgroundIndex];
            const isDark = this.shareBackgroundIndex >= 2; // Dark and Light (Light uses dark text)
            const isLight = this.shareBackgroundIndex === 3;

            canvas.width = 1080;
            canvas.height = 1080;

            // Draw gradient background
            const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, bg.colors[0]);
            gradient.addColorStop(1, bg.colors[1]);
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Text color
            const textColor = isLight ? '#1a1a2e' : '#ffffff';
            const subtextColor = isLight ? '#4a5568' : 'rgba(255,255,255,0.8)';
            const brandColor = isLight ? '#6b7280' : 'rgba(255,255,255,0.5)';

            // Word wrap helper
            function wrapText(ctx, text, maxWidth) {
                const words = text.split(' ');
                const lines = [];
                let currentLine = '';
                for (const word of words) {
                    const testLine = currentLine ? currentLine + ' ' + word : word;
                    if (ctx.measureText(testLine).width > maxWidth && currentLine) {
                        lines.push(currentLine);
                        currentLine = word;
                    } else {
                        currentLine = testLine;
                    }
                }
                if (currentLine) lines.push(currentLine);
                return lines;
            }

            const verseText = this.getShareVerseText();
            const reference = this.getShareReference() + ' (' + this.translation + ')';
            const padding = 80;
            const maxWidth = canvas.width - padding * 2;

            // Determine font size based on text length
            let fontSize = 42;
            if (verseText.length > 400) fontSize = 30;
            else if (verseText.length > 250) fontSize = 34;
            else if (verseText.length > 150) fontSize = 38;

            // Draw verse text
            ctx.font = `${fontSize}px Georgia, "Times New Roman", serif`;
            ctx.fillStyle = textColor;
            ctx.textAlign = 'center';

            const lines = wrapText(ctx, `"${verseText}"`, maxWidth);
            const lineHeight = fontSize * 1.5;
            const totalTextHeight = lines.length * lineHeight;
            const startY = (canvas.height - totalTextHeight) / 2 - 30;

            lines.forEach((line, i) => {
                ctx.fillText(line, canvas.width / 2, startY + i * lineHeight);
            });

            // Draw reference
            ctx.font = `28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
            ctx.fillStyle = subtextColor;
            ctx.fillText(reference, canvas.width / 2, startY + totalTextHeight + 40);

            // Draw branding
            ctx.font = `18px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
            ctx.fillStyle = brandColor;
            ctx.fillText('In the Word', canvas.width / 2, canvas.height - 40);

            this.shareImagePreview = canvas.toDataURL('image/png');
        },

        selectShareBackground(index) {
            this.shareBackgroundIndex = index;
            this.generateVerseImagePreview();
        },

        async downloadShareImage() {
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            canvas.toBlob((blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${this.getShareReference().replace(/[\s:]/g, '-')}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                this.showToast('Image downloaded', 'success');
            }, 'image/png');
        },

        async shareImage() {
            if (!navigator.share || !navigator.canShare) return;
            const canvas = document.getElementById('share-canvas');
            if (!canvas) return;

            canvas.toBlob(async (blob) => {
                const file = new File([blob], 'verse.png', { type: 'image/png' });
                if (navigator.canShare({ files: [file] })) {
                    try {
                        await navigator.share({
                            files: [file],
                            title: this.getShareReference(),
                            text: this.getShareReference()
                        });
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            console.error('Share image failed:', err);
                        }
                    }
                }
            }, 'image/png');
        },
};
