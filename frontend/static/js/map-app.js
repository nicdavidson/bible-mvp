// Cross-Reference Map — Alpine.js Application Component
// Extracted from map.html for modularity

// ========== Alpine component ==========
// Popular verse suggestions for search
const SUGGESTIONS = [
    { ref: 'John 3:16', desc: 'God\'s love' },
    { ref: 'Romans 8:28', desc: 'All things work' },
    { ref: 'Psalm 23:1', desc: 'The Lord is my shepherd' },
    { ref: 'Genesis 1:1', desc: 'In the beginning' },
    { ref: 'Isaiah 53:5', desc: 'By His wounds' },
    { ref: 'Proverbs 3:5', desc: 'Trust in the LORD' },
    { ref: 'Matthew 28:19', desc: 'Great Commission' },
    { ref: 'Philippians 4:13', desc: 'I can do all things' },
    { ref: 'Jeremiah 29:11', desc: 'Plans to prosper' },
    { ref: 'Romans 3:23', desc: 'All have sinned' },
    { ref: 'Ephesians 2:8', desc: 'Saved by grace' },
    { ref: 'Revelation 21:4', desc: 'No more tears' },
    { ref: '1 Corinthians 13:4', desc: 'Love is patient' },
    { ref: 'Hebrews 11:1', desc: 'Faith defined' },
    { ref: 'Matthew 5:14', desc: 'Light of the world' },
    { ref: 'Romans 12:2', desc: 'Be transformed' },
];

function crossRefApp() {
    return {
        query: 'John 3:16',
        depth: 1,
        perVerse: 5,
        diminish: false,
        maxNodes: 150,
        colorMode: 'testament',
        groupMode: 'none',
        showGroupLabels: true,
        showHeatmap: false,
        pathMode: 'strongest',
        filterMode: 'none',
        filterValue: '',
        selectedBooks: [],
        filterDim: true,
        _bookFilterTimer: null,
        controlsOpen: true,
        showSuggestions: false,
        loading: false,
        loadingMsg: 'Loading cross-references...',
        errorMsg: '',
        centerLabel: '',
        tooltip: { show: false, ref: '', text: '', x: 0, y: 0 },
        graph: null,
        currentCenter: '',
        hoveredNode: null,
        selectedNode: null,
        pathTarget: null,
        selectedNodeConnections: 0,
        selectedNodeEdges: [],
        graphStats: { nodes: 0, edges: 0, books: 0, hub: '' },
        _lastData: null,
        expandingNode: false,
        // Points to Jesus mode
        ptjMode: false,
        ptjMethod: 'find-path',
        ptjSeedIds: new Set(),
        ptjPathToChrist: null,
        _savedColorMode: 'testament',
        // Seed verse presets
        ptjPresets: [],
        ptjActivePreset: null,
        ptjSeedToggles: {},
        ptjSeedPanelOpen: false,
        ptjPresetsLoaded: false,
        // Vote thresholds (percentile-based, recomputed per graph)
        voteThresholds: { p75: 300, p50: 150, p25: 75 },
        // Path chain panel
        showPathChain: false,
        pathChainNodes: [],  // ordered array of node objects from the highlighted path
        pathChainEdges: [],  // votes for edge between node[i] and node[i+1]
        chainCopied: false,
        // History & navigation
        history: [],        // [{ref: 'John.3.16', label: 'Jn 3:16', query: 'John 3:16'}]
        historyIndex: -1,
        _isHistoryNav: false,
        // Pinned verses
        pinnedVerses: [],   // [{ref: 'John.3.16', label: 'Jn 3:16', query: 'John 3:16'}]

        filteredSuggestions() {
            const q = this.query.toLowerCase().trim();
            if (!q) return SUGGESTIONS.slice(0, 8);
            return SUGGESTIONS.filter(s =>
                s.ref.toLowerCase().includes(q) || s.desc.toLowerCase().includes(q)
            ).slice(0, 6);
        },

        init() {
            // Load pinned verses from localStorage
            try {
                const saved = localStorage.getItem('crossref-pinned');
                if (saved) this.pinnedVerses = JSON.parse(saved);
            } catch (_) {}

            // Read initial verse from URL hash
            const hash = window.location.hash.slice(1);
            if (hash) {
                this.query = decodeURIComponent(hash.replace(/\+/g, ' '));
            }

            // Listen for browser back/forward
            window.addEventListener('popstate', () => {
                const h = window.location.hash.slice(1);
                if (h) {
                    const q = decodeURIComponent(h.replace(/\+/g, ' '));
                    if (q !== this.query || q !== this.currentCenter) {
                        this.query = q;
                        this._isHistoryNav = true;
                        this.search();
                    }
                }
            });

            this.$nextTick(() => {
                this.graph = new ForceGraph(this.$refs.canvas);
                this.graph.colorMode = this.colorMode;
                this.graph.groupMode = this.groupMode;
                this.graph.pathMode = this.pathMode;
                this.graph.showGroupLabels = this.showGroupLabels;
                this.graph.showHeatmap = this.showHeatmap;
                this.graph.filterMode = this.filterMode;
                this.graph.filterValue = this.filterValue;
                this.graph.selectedBooks = [...this.selectedBooks];
                this.graph.filterDim = this.filterDim;

                this.graph.onHover = (node, sx, sy) => {
                    this.hoveredNode = node;
                    if (node) {
                        this.tooltip.ref = fullLabel(node);
                        this.tooltip.text = node.text || '';
                        let tx = sx + 16;
                        let ty = sy - 10;
                        if (tx + 280 > window.innerWidth) tx = sx - 296;
                        if (ty + 120 > window.innerHeight) ty = sy - 120;
                        if (ty < 60) ty = 60;
                        this.tooltip.x = tx;
                        this.tooltip.y = ty;
                        this.tooltip.show = true;
                    } else {
                        this.tooltip.show = false;
                    }
                };

                this.graph.onClick = (node, event) => {
                    if (!node) {
                        // Click empty space: if awaiting second node (pathTarget set, no selection), cancel targeting
                        if (this.pathTarget && !this.selectedNode) {
                            this.pathTarget = null;
                            this.graph.pathTarget = null;
                        } else {
                            this.selectedNode = null;
                            this.pathTarget = null;
                            this.graph.selectedNode = null;
                            this.graph.pathTarget = null;
                        }
                        this.graph._draw();
                        return;
                    }
                    if (node.isCenter && !node.isChrist) {
                        this.selectedNode = null;
                        this.pathTarget = null;
                        this.graph.selectedNode = null;
                        this.graph.pathTarget = null;
                        this.graph._draw();
                        return;
                    }
                    // Shift+click with existing selection → set as path target (desktop)
                    if (event && event.shiftKey && this.selectedNode && this.selectedNode !== node) {
                        this.pathTarget = node;
                        this.graph.pathTarget = node;
                        this.graph._pathCache.hovNode = null;
                        this.graph._draw();
                        return;
                    }
                    // "Set Target" flow: pathTarget already set, awaiting second node
                    if (this.pathTarget && !this.selectedNode && this.pathTarget !== node) {
                        this.selectedNode = node;
                        this.graph.selectedNode = node;
                        this.graph._pathCache.hovNode = null;
                        this.graph._draw();
                        this._computeSelectedNodeInfo(node);
                        // Auto-open chain view
                        this.$nextTick(() => this.openPathChain());
                        return;
                    }
                    // Normal click → select node
                    this.selectedNode = node;
                    this.graph.selectedNode = node;

                    // In PTJ mode: auto-set Christ as path target to show path to Jesus
                    if (this.ptjMode && !node.isChrist) {
                        const christNode = this.graph.nodeMap['__CHRIST__'];
                        if (christNode) {
                            this.pathTarget = christNode;
                            this.graph.pathTarget = christNode;
                        } else {
                            this.pathTarget = null;
                            this.graph.pathTarget = null;
                        }
                    } else {
                        this.pathTarget = null;
                        this.graph.pathTarget = null;
                    }
                    this.graph._pathCache.hovNode = null; // force recompute
                    this.graph._draw();
                    this._computeSelectedNodeInfo(node);
                };

                this.search();
            });
        },

        _computeSelectedNodeInfo(node) {
            if (!this._lastData || !node) return;
            const edges = this._lastData.edges;
            const connected = [];
            let count = 0;
            for (const e of edges) {
                if (e.source === node.id || e.target === node.id) {
                    count++;
                    const otherId = e.source === node.id ? e.target : e.source;
                    const otherNode = this._lastData.nodes.find(n => n.id === otherId);
                    if (otherNode) {
                        connected.push({
                            id: otherId,
                            label: fullLabel(otherNode),
                            votes: e.votes,
                        });
                    }
                }
            }
            connected.sort((a, b) => b.votes - a.votes);
            this.selectedNodeConnections = count;
            this.selectedNodeEdges = connected;
        },

        togglePointsToJesus() {
            this.ptjMode = !this.ptjMode;
            if (this.ptjMode) {
                this._savedColorMode = this.colorMode;
                this.colorMode = 'christological';
                if (this.graph) this.graph.colorMode = 'christological';
                this.loadPresets().then(() => this.search());
            } else {
                this.colorMode = this._savedColorMode || 'testament';
                if (this.graph) this.graph.colorMode = this.colorMode;
                this.ptjSeedIds = new Set();
                this.ptjPathToChrist = null;
                this.ptjSeedPanelOpen = false;
                if (this.graph) {
                    this.graph.ptjSeedIds = new Set();
                    this.graph.ptjMode = false;
                }
                this.search();
            }
        },

        async expandNode(node) {
            if (!node || !this.graph || this.expandingNode) return;
            this.expandingNode = true;
            try {
                const ref = parseReference(node.book + ' ' + node.chapter + ':' + node.verse);
                const params = new URLSearchParams({ depth: 1, per_verse: 5, limit: 20 });
                const resp = await fetch(`/api/crossref-map/${ref}?${params}`);
                if (!resp.ok) throw new Error('Failed to expand');
                const data = await resp.json();
                if (!data.nodes || data.nodes.length === 0) return;

                // Merge new nodes/edges into existing data
                const existingNodeIds = new Set(this._lastData.nodes.map(n => n.id));
                const existingEdgeKeys = new Set(this._lastData.edges.map(e =>
                    e.source < e.target ? e.source + '|' + e.target : e.target + '|' + e.source
                ));
                let addedNodes = 0, addedEdges = 0;

                for (const newNode of data.nodes) {
                    if (!existingNodeIds.has(newNode.id)) {
                        const expandedGraphNode = this.graph.nodeMap[node.id];
                        newNode.depth = (expandedGraphNode ? expandedGraphNode.depth : node.depth || 1) + 1;
                        this._lastData.nodes.push(newNode);
                        existingNodeIds.add(newNode.id);
                        addedNodes++;
                    }
                }
                for (const newEdge of data.edges) {
                    const key = newEdge.source < newEdge.target
                        ? newEdge.source + '|' + newEdge.target
                        : newEdge.target + '|' + newEdge.source;
                    if (!existingEdgeKeys.has(key) && existingNodeIds.has(newEdge.source) && existingNodeIds.has(newEdge.target)) {
                        this._lastData.edges.push(newEdge);
                        existingEdgeKeys.add(key);
                        addedEdges++;
                    }
                }

                if (addedNodes === 0 && addedEdges === 0) return;

                this._updateStats(this._lastData);
                this.graph.setData(this._lastData.nodes, this._lastData.edges, this._lastData.center || this.currentCenter);

                // Re-select the expanded node
                const reselected = this.graph.nodeMap[node.id];
                if (reselected) {
                    this.selectedNode = reselected;
                    this.graph.selectedNode = reselected;
                    this._computeSelectedNodeInfo(reselected);
                    this.graph._draw();
                }
            } catch (err) {
                this.errorMsg = err.message || 'Failed to expand node';
            } finally {
                this.expandingNode = false;
            }
        },

        _updateStats(data) {
            const books = new Set(data.nodes.map(n => n.book));
            // Find most connected node
            const connCount = {};
            for (const e of data.edges) {
                connCount[e.source] = (connCount[e.source] || 0) + 1;
                connCount[e.target] = (connCount[e.target] || 0) + 1;
            }
            let maxConn = 0, hubId = '';
            for (const [id, c] of Object.entries(connCount)) {
                if (c > maxConn) { maxConn = c; hubId = id; }
            }
            const hubNode = data.nodes.find(n => n.id === hubId);
            const hubLabel = hubNode ? (hubNode.isChrist ? 'Christ' : abbrev(hubNode.book) + ' ' + hubNode.chapter + ':' + hubNode.verse) : '';
            this.graphStats = {
                nodes: data.nodes.length,
                edges: data.edges.length,
                books: books.size,
                hub: hubLabel,
            };
        },

        // --- URL hash sync ---
        _updateHash(q) {
            const hash = '#' + encodeURIComponent(q);
            if (window.location.hash !== hash) {
                if (this._isHistoryNav) {
                    // Don't push new browser history when navigating via breadcrumbs
                    this._isHistoryNav = false;
                } else {
                    window.history.pushState(null, '', hash);
                }
            }
        },

        // --- History management ---
        _pushHistory(q, centerNode) {
            if (this._isHistoryNav) return;
            const label = centerNode ? abbrev(centerNode.book) + ' ' + centerNode.chapter + ':' + centerNode.verse : q;
            const entry = { ref: q, label, query: q };
            // If we navigated back and then searched something new, truncate forward history
            if (this.historyIndex < this.history.length - 1) {
                this.history = this.history.slice(0, this.historyIndex + 1);
            }
            // Don't push duplicates
            if (this.history.length > 0 && this.history[this.history.length - 1].query === q) {
                this.historyIndex = this.history.length - 1;
                return;
            }
            this.history.push(entry);
            // Limit history to 20 entries
            if (this.history.length > 20) this.history.shift();
            this.historyIndex = this.history.length - 1;
        },

        navigateHistory(index) {
            if (index < 0 || index >= this.history.length) return;
            this.historyIndex = index;
            const entry = this.history[index];
            this.query = entry.query;
            this._isHistoryNav = true;
            this.search();
        },

        // --- Verse pinning ---
        pinVerse(node) {
            if (!node) return;
            const q = node.book + ' ' + node.chapter + ':' + node.verse;
            const ref = node.id || q;
            const idx = this.pinnedVerses.findIndex(p => p.ref === ref);
            if (idx >= 0) {
                this.pinnedVerses.splice(idx, 1);
            } else {
                this.pinnedVerses.push({
                    ref,
                    label: abbrev(node.book) + ' ' + node.chapter + ':' + node.verse,
                    query: q,
                });
            }
            this.savePins();
        },

        isVersePinned(node) {
            if (!node) return false;
            const ref = node.id || (node.book + ' ' + node.chapter + ':' + node.verse);
            return this.pinnedVerses.some(p => p.ref === ref);
        },

        savePins() {
            try {
                localStorage.setItem('crossref-pinned', JSON.stringify(this.pinnedVerses));
            } catch (_) {}
        },

        pinCenter() {
            if (!this._lastData || !this.currentCenter) return;
            const centerNode = this._lastData.nodes.find(n => n.id === this.currentCenter);
            if (centerNode) this.pinVerse(centerNode);
        },

        isCenterPinned() {
            if (!this.currentCenter) return false;
            return this.pinnedVerses.some(p => p.ref === this.currentCenter);
        },

        async search() {
            const q = this.query.trim();
            if (!q) return;

            this.loading = true;
            this.errorMsg = '';
            this.tooltip.show = false;
            this.selectedNode = null;
            this.pathTarget = null;

            if (this.ptjMode) {
                this.loadingMsg = this.ptjMethod === 'find-path'
                    ? 'Finding path from ' + q + ' to Christ...'
                    : 'Loading Points to Jesus (' + this.ptjMethod.replace('-', ' ') + ')...';
            } else {
                this.loadingMsg = 'Loading cross-references for ' + q + '...';
            }

            try {
                let url;
                if (this.ptjMode) {
                    const params = new URLSearchParams({
                        method: this.ptjMethod,
                        depth: this.depth,
                        per_verse: this.perVerse,
                        limit: this.maxNodes,
                    });
                    if (this.ptjMethod === 'find-path') {
                        if (!q) {
                            this.errorMsg = 'Enter a verse to find its path to Christ';
                            this.loading = false;
                            return;
                        }
                        params.set('verse', q);
                    }
                    // Send custom seed list if user has toggled some off
                    const customSeeds = this._getActiveSeeds();
                    if (customSeeds) params.set('seeds', customSeeds);
                    url = `/api/crossref-map/christological?${params}`;
                } else {
                    const ref = parseReference(q);
                    const params = new URLSearchParams({
                        depth: this.depth,
                        per_verse: this.perVerse,
                        limit: this.maxNodes,
                    });
                    if (this.diminish) params.set('diminish', 'true');
                    if (this.filterMode === 'book' && this.selectedBooks.length > 0) {
                        params.set('focus_books', this.selectedBooks.join(','));
                    }
                    url = `/api/crossref-map/${ref}?${params}`;
                }
                const resp = await fetch(url);

                if (!resp.ok) {
                    const body = await resp.text();
                    let msg = 'Failed to load cross-references';
                    try {
                        const j = JSON.parse(body);
                        if (j.detail) msg = j.detail;
                    } catch (_) {
                        if (body) msg = body;
                    }
                    throw new Error(msg);
                }

                const data = await resp.json();

                if (!data.nodes || data.nodes.length === 0) {
                    this.errorMsg = 'No cross-references found for ' + q;
                    this.loading = false;
                    return;
                }

                // Store PTJ metadata
                if (this.ptjMode && data.seedIds) {
                    this.ptjSeedIds = new Set(data.seedIds);
                    this.ptjPathToChrist = data.pathToChrist || null;
                    if (this.graph) {
                        this.graph.ptjSeedIds = this.ptjSeedIds;
                        this.graph.ptjMode = true;
                    }
                }

                this._lastData = data;
                const centerNode = data.nodes.find(n => n.id === data.center);

                // Set center label
                if (this.ptjMode && this.ptjMethod === 'find-path') {
                    if (data.pathToChrist && data.foundSeed) {
                        this.centerLabel = q + ' \u2192 Christ';
                    } else {
                        this.centerLabel = q + ' (no path found)';
                        this.errorMsg = 'No cross-reference path found from ' + q + ' to Christ within 6 hops. Try a different verse.';
                    }
                } else if (centerNode && centerNode.isChrist) {
                    this.centerLabel = 'Points to Jesus';
                } else {
                    this.centerLabel = centerNode ? fullLabel(centerNode) : data.center;
                }
                this.currentCenter = data.center;

                // Update URL and history
                if (!this.ptjMode) {
                    this._updateHash(q);
                    this._pushHistory(q, centerNode);
                }

                this._updateStats(data);
                this._computeVoteThresholds(data.edges);
                this.graph.setData(data.nodes, data.edges, data.center);

                // Find-path: auto-highlight the path
                if (this.ptjMode && this.ptjMethod === 'find-path' && data.pathToChrist && data.pathToChrist.length > 0) {
                    this.$nextTick(() => {
                        const startNode = this.graph.nodeMap[data.center];
                        const christNode = this.graph.nodeMap['__CHRIST__'];
                        if (startNode && christNode) {
                            this.selectedNode = startNode;
                            this.pathTarget = christNode;
                            this.graph.selectedNode = startNode;
                            this.graph.pathTarget = christNode;
                            this.graph._pathCache.hovNode = null; // force recompute
                            this.graph._draw();
                        }
                    });
                }
            } catch (err) {
                this.errorMsg = err.message || 'An error occurred';
            } finally {
                this.loading = false;
                this._isHistoryNav = false;
            }
        },

        applyBookFilter() {
            // Sync to graph for immediate visual filtering
            if (this.graph) {
                this.graph.selectedBooks = [...this.selectedBooks];
                this.graph._draw();
            }
            // Debounced re-query to load focused data from API
            clearTimeout(this._bookFilterTimer);
            this._bookFilterTimer = setTimeout(() => {
                if (this.currentCenter) this.search();
            }, 600);
        },

        resetView() {
            if (this.graph) this.graph.resetView();
            this.selectedNode = null;
            this.pathTarget = null;
            if (this.graph) { this.graph.selectedNode = null; this.graph.pathTarget = null; }
        },

        openPathChain() {
            if (!this.graph || !this.graph._pathCache) return;
            const ordered = this.graph._pathCache.orderedPath || [];
            if (ordered.length < 2) return;
            this.pathChainNodes = ordered;
            // Look up edge votes between consecutive nodes
            this.pathChainEdges = [];
            for (let i = 0; i < ordered.length - 1; i++) {
                const a = ordered[i], b = ordered[i + 1];
                const edge = this.graph.edges.find(e =>
                    (e.source === a && e.target === b) || (e.source === b && e.target === a)
                );
                this.pathChainEdges.push(edge ? edge.votes : 0);
            }
            this.showPathChain = true;
        },

        setAsTarget(node) {
            if (!node || !this.graph) return;
            this.pathTarget = node;
            this.graph.pathTarget = node;
            this.graph._pathCache.hovNode = null; // force recompute
            this.graph._draw();
            // Clear selection so user can tap the next node
            this.selectedNode = null;
            this.graph.selectedNode = null;
        },

        copyChain() {
            if (!this.pathChainNodes || this.pathChainNodes.length < 2) return;
            const hops = this.pathChainNodes.length - 1;
            const lines = this.pathChainNodes.map((node, idx) => {
                const ref = node.isChrist ? 'Christ'
                    : (node.book + ' ' + node.chapter + ':' + node.verse);
                const text = node.text ? ' \u2014 "' + node.text + '"' : '';
                return (idx + 1) + '. ' + ref + text;
            });
            const header = 'Cross-Reference Chain (' + hops + ' hop' + (hops !== 1 ? 's' : '') + ')';
            const footer = '\nShared from In the Word';
            const fullText = header + '\n\n' + lines.join('\n\n') + footer;
            navigator.clipboard.writeText(fullText).then(() => {
                this.chainCopied = true;
                setTimeout(() => this.chainCopied = false, 2000);
            }).catch(() => {
                this.errorMsg = 'Could not copy to clipboard';
            });
        },

        async shareChain() {
            if (!navigator.share || !this.pathChainNodes || this.pathChainNodes.length < 2) return;
            const startNode = this.pathChainNodes[0];
            const endNode = this.pathChainNodes[this.pathChainNodes.length - 1];
            const startLabel = startNode.isChrist ? 'Christ'
                : (startNode.book + ' ' + startNode.chapter + ':' + startNode.verse);
            const endLabel = endNode.isChrist ? 'Christ'
                : (endNode.book + ' ' + endNode.chapter + ':' + endNode.verse);
            const title = 'Cross-Reference Chain: ' + startLabel + ' \u2192 ' + endLabel;
            const lines = this.pathChainNodes.map((node, idx) => {
                const ref = node.isChrist ? 'Christ'
                    : (node.book + ' ' + node.chapter + ':' + node.verse);
                const text = node.text ? ' \u2014 "' + node.text + '"' : '';
                return (idx + 1) + '. ' + ref + text;
            });
            const fullText = title + '\n\n' + lines.join('\n\n') + '\n\nShared from In the Word';
            try {
                await navigator.share({ title, text: fullText });
            } catch (err) {
                if (err.name !== 'AbortError') this.errorMsg = 'Share failed';
            }
        },

        // --- Seed verse presets ---
        async loadPresets() {
            if (this.ptjPresetsLoaded) return;
            try {
                const resp = await fetch('/api/crossref-map/presets');
                if (!resp.ok) throw new Error('Failed to load presets');
                const data = await resp.json();
                this.ptjPresets = data.presets;
                this.ptjPresetsLoaded = true;
                // Auto-select preset matching current method
                if (!this.ptjActivePreset) {
                    const match = this.ptjPresets.find(p => p.id === this.ptjMethod);
                    if (match) this._initPreset(match);
                }
            } catch (err) {
                this.errorMsg = 'Could not load seed verse presets';
            }
        },

        selectPreset(presetId) {
            const preset = this.ptjPresets.find(p => p.id === presetId);
            if (!preset) return;
            this.ptjMethod = presetId;
            this._initPreset(preset);
            this.search();
        },

        _initPreset(preset) {
            this.ptjActivePreset = preset;
            this.ptjSeedToggles = {};
            for (const seed of preset.seeds) {
                this.ptjSeedToggles[seed.id] = true;
            }
            this._loadSeedToggles();
        },

        toggleSeed(seedId) {
            this.ptjSeedToggles[seedId] = !this.ptjSeedToggles[seedId];
            this._saveSeedToggles();
            this.search();
        },

        _saveSeedToggles() {
            try {
                localStorage.setItem('ptj-seed-toggles', JSON.stringify({
                    preset: this.ptjMethod,
                    toggles: this.ptjSeedToggles,
                }));
            } catch (_) {}
        },

        _loadSeedToggles() {
            try {
                const saved = localStorage.getItem('ptj-seed-toggles');
                if (saved) {
                    const data = JSON.parse(saved);
                    if (data.preset === this.ptjMethod && data.toggles) {
                        for (const [id, val] of Object.entries(data.toggles)) {
                            if (id in this.ptjSeedToggles) {
                                this.ptjSeedToggles[id] = val;
                            }
                        }
                    }
                }
            } catch (_) {}
        },

        _getActiveSeeds() {
            if (!this.ptjActivePreset) return null;
            const all = this.ptjActivePreset.seeds;
            const active = all.filter(s => this.ptjSeedToggles[s.id] !== false);
            if (active.length === all.length || active.length === 0) return null;
            return active.map(s => s.id).join(',');
        },

        _getActiveSeedCount() {
            if (!this.ptjActivePreset) return 0;
            return this.ptjActivePreset.seeds.filter(s => this.ptjSeedToggles[s.id] !== false).length;
        },

        _allSeedsOn() {
            if (!this.ptjActivePreset) return;
            for (const seed of this.ptjActivePreset.seeds) {
                this.ptjSeedToggles[seed.id] = true;
            }
            this._saveSeedToggles();
            this.search();
        },

        _allSeedsOff() {
            if (!this.ptjActivePreset) return;
            for (const seed of this.ptjActivePreset.seeds) {
                this.ptjSeedToggles[seed.id] = false;
            }
            this._saveSeedToggles();
        },

        // --- Vote thresholds (percentile-based) ---
        _computeVoteThresholds(edges) {
            if (!edges || edges.length < 4) return;
            const votes = edges.map(e => e.votes || 0).filter(v => v > 0).sort((a, b) => a - b);
            if (votes.length < 4) return;
            this.voteThresholds = {
                p75: votes[Math.floor(votes.length * 0.75)] || 1,
                p50: votes[Math.floor(votes.length * 0.50)] || 1,
                p25: votes[Math.floor(votes.length * 0.25)] || 1,
            };
        },

        voteColor(v) {
            const t = this.voteThresholds;
            if (v >= t.p75) return '#22c55e';
            if (v >= t.p50) return '#38bdf8';
            if (v >= t.p25) return '#eab308';
            return 'var(--border)';
        },

        voteWidth(v) {
            const t = this.voteThresholds;
            if (v >= t.p75) return '4px';
            if (v >= t.p50) return '3px';
            if (v >= t.p25) return '2px';
            return '1px';
        },

        voteDotColor(v) {
            const t = this.voteThresholds;
            if (v >= t.p75) return '#22c55e';
            if (v >= t.p50) return '#38bdf8';
            if (v >= t.p25) return '#eab308';
            return '#94a3b8';
        },

        selectChainNode(node) {
            if (!this.graph || !node) return;
            this.selectedNode = node;
            this.graph.selectedNode = node;
            // Center camera on the node
            this.graph.camX = node.x * this.graph.zoom;
            this.graph.camY = node.y * this.graph.zoom;
            this.graph._draw();
            this._computeSelectedNodeInfo(node);
        },

        exportImage() {
            const canvas = this.$refs.canvas;
            if (!canvas) return;
            const dataURL = canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.href = dataURL;
            const name = (this.currentCenter || 'crossref-map')
                .toLowerCase().replace(/\s+/g, '-').replace(/:/g, '-');
            a.download = `crossref-${name}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        },
    };
}
