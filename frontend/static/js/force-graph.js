// Cross-Reference Map — ForceGraph Physics Engine
// Extracted from map.html for modularity

// ========== Force simulation ==========
class ForceGraph {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.nodeMap = {};

        // Camera
        this.camX = 0;
        this.camY = 0;
        this.zoom = 1;

        // Physics
        this.repulsion = 6000;
        this.springLen = 160;
        this.springK = 0.004;
        this.gravity = 0.015;
        this.damping = 0.85;
        this.settled = false;
        this.running = false;
        this.tickCount = 0;
        this.maxTicks = 600;

        // Interaction
        this.dragNode = null;
        this.hoveredNode = null;
        this.isPanning = false;
        this.panStart = { x: 0, y: 0 };
        this.camStart = { x: 0, y: 0 };

        // Pinch zoom
        this.lastPinchDist = 0;

        // DPR
        this.dpr = window.devicePixelRatio || 1;

        this.onHover = null;  // callback(node, screenX, screenY) or null
        this.onClick = null;  // callback(node)
        this.colorMode = 'testament';  // testament | book | genre | depth
        this.groupMode = 'none';      // none | depth | testament | book | genre
        this.pathMode = 'strongest';  // shortest | strongest
        this.showGroupLabels = true;
        this.showHeatmap = false;
        this.filterMode = 'none';
        this.filterValue = '';
        this.selectedBooks = [];
        this.filterDim = true;
        this.selectedNode = null; // currently selected node (for info panel)
        this.pathTarget = null;   // second node for two-node path
        this.frameCount = 0; // for animations
        this._animating = false; // continuous animation for pulse
        this.ptjMode = false;
        this.ptjSeedIds = new Set();

        // Cached path-finding results (recomputed only on hover/selection change)
        this._pathCache = { hovNode: null, selNode: null, _pathTarget: null, pathNodes: new Set(), pathEdges: new Set(), orderedPath: [], hasActive: false };

        this._resize();
        this._bindEvents();
    }

    _resize() {
        const rect = this.canvas.getBoundingClientRect();
        this.w = rect.width;
        this.h = rect.height;
        this.canvas.width = this.w * this.dpr;
        this.canvas.height = this.h * this.dpr;
        this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    }

    _bindEvents() {
        window.addEventListener('resize', () => this._resize());

        // --- Mouse ---
        this.canvas.addEventListener('mousedown', (e) => this._onPointerDown(e.clientX, e.clientY, e));
        window.addEventListener('mousemove', (e) => this._onPointerMove(e.clientX, e.clientY, e));
        window.addEventListener('mouseup', (e) => this._onPointerUp(e));
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.08 : 1 / 1.08;
            this._zoomAt(e.clientX, e.clientY, zoomFactor);
        }, { passive: false });

        // --- Touch ---
        this.canvas.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                this._onPointerDown(e.touches[0].clientX, e.touches[0].clientY, e);
            } else if (e.touches.length === 2) {
                this.dragNode = null;
                this.isPanning = false;
                this.lastPinchDist = this._pinchDist(e);
            }
        }, { passive: false });
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (e.touches.length === 1) {
                this._onPointerMove(e.touches[0].clientX, e.touches[0].clientY, e);
            } else if (e.touches.length === 2) {
                const dist = this._pinchDist(e);
                if (this.lastPinchDist > 0) {
                    const mid = this._pinchMid(e);
                    this._zoomAt(mid.x, mid.y, dist / this.lastPinchDist);
                }
                this.lastPinchDist = dist;
            }
        }, { passive: false });
        this.canvas.addEventListener('touchend', (e) => {
            this.lastPinchDist = 0;
            this._onPointerUp(e);
        });
    }

    _pinchDist(e) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    _pinchMid(e) {
        return {
            x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
            y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
        };
    }

    _zoomAt(screenX, screenY, factor) {
        const oldZoom = this.zoom;
        this.zoom = Math.max(0.15, Math.min(5, this.zoom * factor));
        const realFactor = this.zoom / oldZoom;
        // Adjust camera so the point under the cursor stays fixed
        const cx = this.w / 2;
        const cy = this.h / 2;
        this.camX = screenX - cx + realFactor * (this.camX - screenX + cx);
        this.camY = screenY - cy + realFactor * (this.camY - screenY + cy);
        this._draw();
    }

    _screenToWorld(sx, sy) {
        const cx = this.w / 2;
        const cy = this.h / 2;
        return {
            x: (sx - cx + this.camX) / this.zoom,
            y: (sy - cy + this.camY) / this.zoom,
        };
    }

    _worldToScreen(wx, wy) {
        const cx = this.w / 2;
        const cy = this.h / 2;
        return {
            x: wx * this.zoom - this.camX + cx,
            y: wy * this.zoom - this.camY + cy,
        };
    }

    _nodeAt(sx, sy) {
        const wp = this._screenToWorld(sx, sy);
        // Search in reverse to pick topmost (drawn last)
        for (let i = this.nodes.length - 1; i >= 0; i--) {
            const n = this.nodes[i];
            const dx = wp.x - n.x;
            const dy = wp.y - n.y;
            const r = n.radius + 4; // small hit tolerance
            if (dx * dx + dy * dy < r * r) return n;
        }
        return null;
    }

    _onPointerDown(sx, sy, e) {
        const node = this._nodeAt(sx, sy);
        if (node) {
            e.preventDefault();
            this.dragNode = node;
            node.pinned = true;
            this._wake();
        } else {
            this.isPanning = true;
            this.panStart = { x: sx, y: sy };
            this.camStart = { x: this.camX, y: this.camY };
        }
        this._pointerDownPos = { x: sx, y: sy };
    }

    _onPointerMove(sx, sy, e) {
        if (this.dragNode) {
            const wp = this._screenToWorld(sx, sy);
            this.dragNode.x = wp.x;
            this.dragNode.y = wp.y;
            this.dragNode.vx = 0;
            this.dragNode.vy = 0;
            this._wake();
        } else if (this.isPanning) {
            this.camX = this.camStart.x - (sx - this.panStart.x);
            this.camY = this.camStart.y - (sy - this.panStart.y);
            this._draw();
        } else {
            // Hover
            const node = this._nodeAt(sx, sy);
            if (node !== this.hoveredNode) {
                this.hoveredNode = node;
                this.canvas.style.cursor = node ? 'pointer' : 'default';
                if (this.onHover) {
                    if (node) {
                        const sp = this._worldToScreen(node.x, node.y);
                        this.onHover(node, sp.x, sp.y);
                    } else {
                        this.onHover(null, 0, 0);
                    }
                }
                this._draw();
            }
        }
    }

    _onPointerUp(e) {
        const dp = this._pointerDownPos;
        if (this.dragNode) {
            // If barely moved, treat as click
            if (dp && e.changedTouches) {
                const t = e.changedTouches[0];
                if (t) {
                    const dx = t.clientX - dp.x;
                    const dy = t.clientY - dp.y;
                    if (dx * dx + dy * dy < 25 && this.onClick) {
                        this.onClick(this.dragNode, e);
                    }
                }
            } else if (dp) {
                const dx = (e.clientX || 0) - dp.x;
                const dy = (e.clientY || 0) - dp.y;
                if (dx * dx + dy * dy < 25 && this.onClick) {
                    this.onClick(this.dragNode, e);
                }
            }
            this.dragNode.pinned = false;
            this.dragNode = null;
        } else if (this.isPanning && dp) {
            // Click on empty space (barely moved) → deselect
            const sx = e.changedTouches ? e.changedTouches[0].clientX : (e.clientX || 0);
            const sy = e.changedTouches ? e.changedTouches[0].clientY : (e.clientY || 0);
            const dx = sx - dp.x;
            const dy = sy - dp.y;
            if (dx * dx + dy * dy < 25) {
                this.selectedNode = null;
                this.pathTarget = null;
                this._draw();
                if (this.onClick) this.onClick(null, e);
            }
        }
        this.isPanning = false;
        this._pointerDownPos = null;
    }

    setData(nodes, edges, centerId) {
        this.nodeMap = {};
        this.settled = false;
        this.tickCount = 0;

        // Create node objects with physics state
        this.nodes = nodes.map((n, i) => {
            // Spread initial positions in a circle
            const angle = (i / nodes.length) * Math.PI * 2;
            const dist = n.depth === 0 ? 0 : (80 + n.depth * 60 + Math.random() * 40);
            const obj = {
                ...n,
                x: Math.cos(angle) * dist + (Math.random() - 0.5) * 20,
                y: Math.sin(angle) * dist + (Math.random() - 0.5) * 20,
                vx: 0,
                vy: 0,
                radius: n.depth === 0 ? 20 : Math.max(8, 14 - n.depth * 3),
                pinned: false,
                isCenter: n.id === centerId,
            };
            // Christ node: pinned at center, large radius
            if (n.isChrist) {
                obj.x = 0;
                obj.y = 0;
                obj.pinned = true;
                obj.radius = 30;
                obj.isChrist = true;
            }
            if (n.isSeed) {
                obj.isSeed = true;
            }
            this.nodeMap[n.id] = obj;
            return obj;
        });

        // Resolve edge references
        this.edges = edges.map(e => ({
            source: this.nodeMap[e.source],
            target: this.nodeMap[e.target],
            votes: e.votes,
        })).filter(e => e.source && e.target);

        // Compute max votes for scaling
        this.maxVotes = Math.max(1, ...this.edges.map(e => e.votes));

        // Scale node radius by connection count
        const connCount = {};
        for (const e of this.edges) {
            connCount[e.source.id] = (connCount[e.source.id] || 0) + 1;
            connCount[e.target.id] = (connCount[e.target.id] || 0) + 1;
        }
        const maxConn = Math.max(1, ...Object.values(connCount));
        this._maxConnCount = maxConn;
        for (const n of this.nodes) {
            const count = connCount[n.id] || 0;
            n._connCount = count;
            if (n.isCenter) {
                n.radius = 22 + (count / maxConn) * 8;
            } else {
                n.radius = 6 + (count / maxConn) * 12;
            }
        }

        // Reset camera and path cache
        this.camX = 0;
        this.camY = 0;
        this.zoom = 1;
        this._pathCache = { hovNode: null, selNode: null, _pathTarget: null, pathNodes: new Set(), pathEdges: new Set(), orderedPath: [], hasActive: false };

        this._wake();
    }

    _wake() {
        this.settled = false;
        this.tickCount = 0;
        this._animating = false; // stop idle animation
        if (!this.running) {
            this.running = true;
            this._loop();
        }
    }

    _loop() {
        if (!this.running) return;
        this._tick();
        this._draw();
        if (this.settled || this.tickCount > this.maxTicks) {
            this.running = false;
            this._draw();
            // Start idle animation loop for center pulse
            if (!this._animating) {
                this._animating = true;
                this._idleAnimate();
            }
        } else {
            requestAnimationFrame(() => this._loop());
        }
    }

    _idleAnimate() {
        if (this.running) { this._animating = false; return; }
        this.frameCount++;
        // Throttle idle redraws to ~15fps (every 4th frame) — the center pulse doesn't need 60fps
        if (this.frameCount % 4 === 0) this._draw();
        requestAnimationFrame(() => this._idleAnimate());
    }

    _tick() {
        this.tickCount++;
        const nodes = this.nodes;
        const edges = this.edges;
        const N = nodes.length;

        // Reset forces
        for (let i = 0; i < N; i++) { nodes[i].fx = 0; nodes[i].fy = 0; }

        // Repulsion using spatial grid for O(n) approximate repulsion
        // Only compute repulsion for nodes within a cutoff distance
        const cutoff = 400;
        const cellSize = cutoff;
        const grid = new Map();

        // Build spatial grid
        for (let i = 0; i < N; i++) {
            const n = nodes[i];
            const cx = Math.floor(n.x / cellSize);
            const cy = Math.floor(n.y / cellSize);
            const key = cx + ',' + cy;
            if (!grid.has(key)) grid.set(key, []);
            grid.get(key).push(i);
        }

        // Compute repulsion only between nearby cells
        for (const [key, indices] of grid) {
            const [cx, cy] = key.split(',').map(Number);
            // Check this cell and 8 neighbors
            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    const neighborKey = (cx + dx) + ',' + (cy + dy);
                    const neighborIndices = grid.get(neighborKey);
                    if (!neighborIndices) continue;

                    for (const i of indices) {
                        const startJ = (key === neighborKey) ? indices.indexOf(i) + 1 : 0;
                        const arr = (key === neighborKey) ? indices : neighborIndices;
                        for (let ji = startJ; ji < arr.length; ji++) {
                            const j = arr[ji];
                            if (i === j) continue;
                            const a = nodes[i], b = nodes[j];
                            let ddx = b.x - a.x;
                            let ddy = b.y - a.y;
                            let dist2 = ddx * ddx + ddy * ddy;
                            if (dist2 > cutoff * cutoff) continue;
                            if (dist2 < 1) { ddx = Math.random() - 0.5; ddy = Math.random() - 0.5; dist2 = 1; }
                            const dist = Math.sqrt(dist2);
                            const force = this.repulsion / dist2;
                            const fx = (ddx / dist) * force;
                            const fy = (ddy / dist) * force;
                            a.fx -= fx; a.fy -= fy;
                            b.fx += fx; b.fy += fy;
                        }
                    }
                }
            }
        }

        // Long-range repulsion: aggregate distant cells into center-of-mass
        // This keeps clusters from overlapping without O(n²) cost
        const cellCenters = [];
        for (const [key, indices] of grid) {
            let mx = 0, my = 0;
            for (const i of indices) { mx += nodes[i].x; my += nodes[i].y; }
            mx /= indices.length; my /= indices.length;
            cellCenters.push({ x: mx, y: my, count: indices.length, key });
        }
        for (let i = 0; i < N; i++) {
            const n = nodes[i];
            for (const cc of cellCenters) {
                let ddx = n.x - cc.x;
                let ddy = n.y - cc.y;
                let dist2 = ddx * ddx + ddy * ddy;
                if (dist2 < cutoff * cutoff) continue; // already handled
                const dist = Math.sqrt(dist2);
                const force = this.repulsion * cc.count * 0.3 / dist2;
                n.fx += (ddx / dist) * force;
                n.fy += (ddy / dist) * force;
            }
        }

        // Spring attraction along edges
        for (const e of edges) {
            const a = e.source, b = e.target;
            let dx = b.x - a.x;
            let dy = b.y - a.y;
            let dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 1) dist = 1;
            const displacement = dist - this.springLen;
            const force = this.springK * displacement;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            a.fx += fx; a.fy += fy;
            b.fx -= fx; b.fy -= fy;
        }

        // Center gravity
        for (let i = 0; i < N; i++) {
            nodes[i].fx -= nodes[i].x * this.gravity;
            nodes[i].fy -= nodes[i].y * this.gravity;
        }

        // Grouping forces — pull nodes toward cluster target positions
        if (this.groupMode !== 'none') {
            const groupK = 0.08; // strength of grouping pull
            const targets = this._getGroupTargets(nodes);
            for (let i = 0; i < N; i++) {
                const n = nodes[i];
                if (n.isCenter) continue; // center stays at origin
                const t = targets[i];
                if (t) {
                    nodes[i].fx += (t.x - n.x) * groupK;
                    nodes[i].fy += (t.y - n.y) * groupK;
                }
            }
        }

        // Integrate
        let totalV = 0;
        for (let i = 0; i < N; i++) {
            const n = nodes[i];
            if (n.pinned) continue;
            n.vx = (n.vx + n.fx) * this.damping;
            n.vy = (n.vy + n.fy) * this.damping;
            const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
            if (speed > 10) {
                n.vx = (n.vx / speed) * 10;
                n.vy = (n.vy / speed) * 10;
            }
            n.x += n.vx;
            n.y += n.vy;
            totalV += speed;
        }

        if (totalV < 0.3 && this.tickCount > 30) {
            this.settled = true;
        }
    }

    // Recompute cached paths when hover/selection/pathMode changes
    _updatePaths() {
        const hov = this.hoveredNode;
        const sel = this.selectedNode;
        const pt = this.pathTarget;
        const cache = this._pathCache;
        if (cache.hovNode === hov && cache.selNode === sel && cache._pathTarget === pt && cache._pathMode === this.pathMode) return;
        cache.hovNode = hov;
        cache.selNode = sel;
        cache._pathTarget = pt;
        cache._pathMode = this.pathMode;

        const centerNode = this.nodes.find(n => n.isCenter);

        // Generic pathfinding between any two nodes
        const findPathBetween = (startNode, targetNode) => {
            const pNodes = new Set();
            const pEdges = new Set();
            if (!targetNode || !startNode || targetNode === startNode) return { nodes: pNodes, edges: pEdges, ordered: [] };

            const adjMap = new Map();
            for (let ei = 0; ei < this.edges.length; ei++) {
                const e = this.edges[ei];
                if (!adjMap.has(e.source)) adjMap.set(e.source, []);
                if (!adjMap.has(e.target)) adjMap.set(e.target, []);
                adjMap.get(e.source).push({ node: e.target, edgeIdx: ei, votes: e.votes });
                adjMap.get(e.target).push({ node: e.source, edgeIdx: ei, votes: e.votes });
            }

            const parent = new Map();
            if (this.pathMode === 'strongest') {
                const dist = new Map();
                const visited = new Set();
                dist.set(startNode, 0);
                const pq = [{ node: startNode, d: 0 }];
                while (pq.length > 0) {
                    let minIdx = 0;
                    for (let i = 1; i < pq.length; i++) { if (pq[i].d < pq[minIdx].d) minIdx = i; }
                    const { node: curr, d: currDist } = pq.splice(minIdx, 1)[0];
                    if (visited.has(curr)) continue;
                    visited.add(curr);
                    if (curr === targetNode) break;
                    for (const { node: neighbor, edgeIdx, votes } of (adjMap.get(curr) || [])) {
                        if (visited.has(neighbor)) continue;
                        const w = 1 / Math.max(1, votes);
                        const alt = currDist + w;
                        if (!dist.has(neighbor) || alt < dist.get(neighbor)) {
                            dist.set(neighbor, alt);
                            parent.set(neighbor, { from: curr, edgeIdx });
                            pq.push({ node: neighbor, d: alt });
                        }
                    }
                }
            } else {
                const visited = new Set();
                const queue = [startNode];
                visited.add(startNode);
                while (queue.length > 0) {
                    const curr = queue.shift();
                    if (curr === targetNode) break;
                    for (const { node: neighbor, edgeIdx } of (adjMap.get(curr) || [])) {
                        if (!visited.has(neighbor)) {
                            visited.add(neighbor);
                            parent.set(neighbor, { from: curr, edgeIdx });
                            queue.push(neighbor);
                        }
                    }
                }
            }

            // Build ordered path from target back to start
            const ordered = [];
            let curr = targetNode;
            while (parent.has(curr)) {
                pNodes.add(curr);
                ordered.push(curr);
                const p = parent.get(curr);
                pEdges.add(p.edgeIdx);
                curr = p.from;
            }
            pNodes.add(startNode);
            ordered.push(startNode);
            ordered.reverse(); // start → target order
            return { nodes: pNodes, edges: pEdges, ordered };
        };

        const emptyResult = { nodes: new Set(), edges: new Set(), ordered: [] };

        // Two-node path: selectedNode <-> pathTarget
        if (sel && pt) {
            const twoNodePath = findPathBetween(sel, pt);
            cache.pathNodes = twoNodePath.nodes;
            cache.pathEdges = twoNodePath.edges;
            cache.orderedPath = twoNodePath.ordered || [];
            cache.hasActive = twoNodePath.nodes.size > 0;
            return;
        }

        // Default: path from center to hovered or selected node
        const hovPath = centerNode ? findPathBetween(centerNode, hov) : emptyResult;
        const selPath = centerNode ? findPathBetween(centerNode, sel) : emptyResult;
        cache.pathNodes = hovPath.nodes.size > 0 ? hovPath.nodes : selPath.nodes;
        cache.pathEdges = hovPath.edges.size > 0 ? hovPath.edges : selPath.edges;
        cache.orderedPath = hovPath.ordered.length > 0 ? hovPath.ordered : (selPath.ordered || []);
        cache.hasActive = !!(hov || sel);
    }

    _draw() {
        const ctx = this.ctx;
        const w = this.w;
        const h = this.h;

        ctx.save();
        ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

        // Background
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, w, h);

        // Subtle grid
        ctx.save();
        const cx = w / 2 - this.camX;
        const cy = h / 2 - this.camY;
        ctx.translate(cx, cy);
        ctx.scale(this.zoom, this.zoom);

        // Use cached path data (updated on hover/selection change, not every frame)
        this._updatePaths();
        const { pathNodes, pathEdges, hasActive } = this._pathCache;

        // Filter helper: does this node match the active filter?
        const _fMode = this.filterMode;
        const _fVal = this.filterValue;
        const _fDim = this.filterDim;
        const _selBooks = this.selectedBooks || [];
        const _fActive = _fMode !== 'none' && (_fMode === 'book' ? _selBooks.length > 0 : _fVal !== '');
        const _nodeMatchesFilter = (n) => {
            if (!_fActive) return true;
            if (_fMode === 'testament') return n.testament === _fVal;
            if (_fMode === 'book') return _selBooks.includes(n.book);
            if (_fMode === 'author') return (BOOK_AUTHORS[n.book] || '') === _fVal;
            return true;
        };

        // Heatmap — radial gradient blobs per node, drawn behind everything
        if (this.showHeatmap) {
            const heatRadius = 80;
            for (const n of this.nodes) {
                if (n.isCenter) continue;
                if (_fActive && !_nodeMatchesFilter(n)) continue;
                const col = getNodeColor(n, this.colorMode, this);
                const rgb = col.rgb || '148,163,184';
                const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, heatRadius);
                grad.addColorStop(0, `rgba(${rgb},0.12)`);
                grad.addColorStop(1, `rgba(${rgb},0)`);
                ctx.fillStyle = grad;
                ctx.fillRect(n.x - heatRadius, n.y - heatRadius, heatRadius * 2, heatRadius * 2);
            }
        }

        // Draw edges (curved to reduce overlap)
        for (let ei = 0; ei < this.edges.length; ei++) {
            const e = this.edges[ei];

            // Filter edges
            const srcMatch = _nodeMatchesFilter(e.source);
            const tgtMatch = _nodeMatchesFilter(e.target);
            const edgeFiltered = _fActive && !srcMatch && !tgtMatch;
            if (edgeFiltered && !_fDim) continue;

            const thick = 0.5 + (e.votes / this.maxVotes) * 3;
            let alpha = 0.12 + (e.votes / this.maxVotes) * 0.25;

            // Highlight states
            const isPathEdge = pathEdges.has(ei);
            if (hasActive && !isPathEdge) {
                alpha *= 0.1; // dim everything not on the trace path
            } else if (isPathEdge) {
                alpha = 0.7 + (e.votes / this.maxVotes) * 0.3;
            }

            // Filter dimming
            if (edgeFiltered && _fDim) alpha *= 0.08;
            else if (_fActive && (!srcMatch || !tgtMatch)) alpha *= 0.3;

            // Curved edge: offset the midpoint perpendicular to the line
            const mx = (e.source.x + e.target.x) / 2;
            const my = (e.source.y + e.target.y) / 2;
            const dx = e.target.x - e.source.x;
            const dy = e.target.y - e.source.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            // Curve amount based on edge index to spread parallel edges
            const curveAmt = (ei % 3 - 1) * Math.min(len * 0.12, 20);
            const cpx = mx + (-dy / len) * curveAmt;
            const cpy = my + (dx / len) * curveAmt;

            ctx.beginPath();
            ctx.moveTo(e.source.x, e.source.y);
            ctx.quadraticCurveTo(cpx, cpy, e.target.x, e.target.y);

            const srcCol = getNodeColor(e.source, this.colorMode, this);
            let edgeColor;
            if (isPathEdge) {
                edgeColor = '255,255,100';
            } else {
                edgeColor = srcCol.rgb || '148,163,184';
            }
            ctx.strokeStyle = `rgba(${edgeColor},${alpha})`;
            ctx.lineWidth = (isPathEdge ? thick * 2 : thick) / this.zoom;
            ctx.stroke();
        }

        // Draw nodes
        // Pulse animation value
        const pulse = 0.5 + 0.5 * Math.sin(this.frameCount * 0.03);

        for (const n of this.nodes) {
            const nodeMatches = _nodeMatchesFilter(n);
            if (_fActive && !nodeMatches && !_fDim) continue;

            const col = getNodeColor(n, this.colorMode, this);
            const baseColor = col.fill;
            const glowColor = col.glow;
            const r = n.radius;
            const isOnPath = pathNodes.has(n);
            const isDimmed = hasActive && !isOnPath;
            const isSelected = n === this.selectedNode;

            if (_fActive && !nodeMatches && _fDim) ctx.globalAlpha = 0.08;
            else if (isDimmed) ctx.globalAlpha = 0.15;

            // ---- Christ node: golden cross with radial glow ----
            if (n.isChrist) {
                // Triple-layer radial glow
                for (let layer = 3; layer >= 1; layer--) {
                    const glowR = r * (1.5 + layer * 1.2) + pulse * 8 * (layer / 3);
                    const alpha = (0.08 + pulse * 0.04) / layer;
                    const grad = ctx.createRadialGradient(n.x, n.y, r * 0.3, n.x, n.y, glowR);
                    grad.addColorStop(0, `rgba(251,191,36,${alpha})`);
                    grad.addColorStop(0.6, `rgba(245,158,11,${alpha * 0.5})`);
                    grad.addColorStop(1, 'rgba(245,158,11,0)');
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
                    ctx.fillStyle = grad;
                    ctx.fill();
                }

                // Cross shape
                const cw = r * 0.35; // cross arm width
                const ch = r * 0.9;  // cross arm height
                const crossTopOffset = r * 0.15; // cross is slightly top-heavy
                ctx.fillStyle = '#fef3c7';
                ctx.shadowColor = 'rgba(251,191,36,0.8)';
                ctx.shadowBlur = 12;
                // Vertical bar
                ctx.fillRect(n.x - cw / 2, n.y - ch - crossTopOffset, cw, ch * 2);
                // Horizontal bar
                ctx.fillRect(n.x - ch * 0.7, n.y - cw / 2 - crossTopOffset, ch * 1.4, cw);
                ctx.shadowBlur = 0;

                // Inner glow circle at center of cross
                const innerGrad = ctx.createRadialGradient(n.x, n.y - crossTopOffset, 0, n.x, n.y - crossTopOffset, r * 0.4);
                innerGrad.addColorStop(0, 'rgba(255,255,255,0.7)');
                innerGrad.addColorStop(1, 'rgba(255,255,255,0)');
                ctx.beginPath();
                ctx.arc(n.x, n.y - crossTopOffset, r * 0.4, 0, Math.PI * 2);
                ctx.fillStyle = innerGrad;
                ctx.fill();

                // "CHRIST" label below
                const christFontSize = Math.max(12, r * 0.5);
                ctx.font = `800 ${christFontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = 'rgba(0,0,0,0.6)';
                ctx.fillText('CHRIST', n.x + 0.5, n.y + ch + 4.5);
                ctx.fillStyle = '#fef3c7';
                ctx.fillText('CHRIST', n.x, n.y + ch + 4);

                if (isDimmed || (_fActive && !nodeMatches && _fDim)) ctx.globalAlpha = 1;
                continue; // skip normal node rendering
            }

            // Glow for center / hovered / selected / path target / path
            if (n.isCenter || n === this.hoveredNode || isSelected || n === this.pathTarget || isOnPath) {
                const glowR = n.isCenter ? r * (2.2 + pulse * 0.6) : r * 2.2;
                const grad = ctx.createRadialGradient(n.x, n.y, r * 0.5, n.x, n.y, glowR);
                if (n.isCenter) {
                    const a = 0.4 + pulse * 0.3;
                    grad.addColorStop(0, glowColor.replace('0.35', String(a)));
                } else if (isSelected) {
                    grad.addColorStop(0, 'rgba(255,255,100,0.4)');
                } else {
                    grad.addColorStop(0, 'rgba(255,255,255,0.2)');
                }
                grad.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.beginPath();
                ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
                ctx.fillStyle = grad;
                ctx.fill();
            }

            // Outer ring for center (pulsing)
            if (n.isCenter) {
                const ringR = r + 3 + pulse * 3;
                ctx.beginPath();
                ctx.arc(n.x, n.y, ringR, 0, Math.PI * 2);
                ctx.strokeStyle = baseColor;
                ctx.lineWidth = 2;
                ctx.globalAlpha = isDimmed ? 0.15 : (0.5 + pulse * 0.5);
                ctx.stroke();
                ctx.globalAlpha = isDimmed ? 0.15 : 1;
            }

            // Selection ring
            if (isSelected) {
                ctx.beginPath();
                ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2);
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 2.5;
                ctx.stroke();
            }

            // Path target ring (second selected node, green)
            if (n === this.pathTarget) {
                ctx.beginPath();
                ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2);
                ctx.strokeStyle = '#22c55e';
                ctx.lineWidth = 2.5;
                ctx.stroke();
            }

            // Node fill
            ctx.beginPath();
            ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
            ctx.fillStyle = baseColor;
            ctx.fill();

            // Hover ring
            if (n === this.hoveredNode && !isSelected) {
                ctx.beginPath();
                ctx.arc(n.x, n.y, r + 2, 0, Math.PI * 2);
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }

            // Seed verse marker (gold ring + tiny cross above)
            if (n.isSeed && this.ptjMode) {
                ctx.beginPath();
                ctx.arc(n.x, n.y, r + 3, 0, Math.PI * 2);
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 1.5;
                ctx.stroke();
                // Tiny cross above
                const tc = 4;
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.moveTo(n.x, n.y - r - 4 - tc);
                ctx.lineTo(n.x, n.y - r - 4 + tc);
                ctx.moveTo(n.x - tc * 0.7, n.y - r - 4);
                ctx.lineTo(n.x + tc * 0.7, n.y - r - 4);
                ctx.stroke();
            }

            // Label — only show when zoomed in enough to read
            const fontSize = Math.max(9, Math.min(14, r * 0.95));
            const screenFontSize = fontSize * this.zoom;
            if (screenFontSize >= 5) {
                const label = shortLabel(n);
                ctx.font = `600 ${fontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                ctx.fillStyle = 'rgba(0,0,0,0.7)';
                ctx.fillText(label, n.x + 0.5, n.y + r + fontSize + 2.5);
                ctx.fillStyle = isOnPath ? '#fef3c7' : '#e2e8f0';
                ctx.fillText(label, n.x, n.y + r + fontSize + 2);
            }

            if (isDimmed || (_fActive && !nodeMatches && _fDim)) ctx.globalAlpha = 1;
        }

        // Group labels — draw at centroid of each cluster
        if (this.groupMode !== 'none' && this.showGroupLabels) {
            const groups = new Map(); // key → { sumX, sumY, count, color, label }
            for (const n of this.nodes) {
                if (n.isCenter) continue;
                let key, label, color;
                if (this.groupMode === 'genre') {
                    key = BOOK_GENRES[n.book] || 'epistle';
                    label = GENRE_LABELS[key] || key;
                    color = GENRE_COLORS[key]?.fill || '#94a3b8';
                } else if (this.groupMode === 'testament') {
                    key = n.testament || 'NT';
                    label = key === 'OT' ? 'Old Testament' : 'New Testament';
                    color = key === 'OT' ? '#f59e0b' : '#38bdf8';
                } else if (this.groupMode === 'depth') {
                    key = n.depth || 1;
                    label = key === 1 ? '1 hop' : key + ' hops';
                    const d = Math.min(key, DEPTH_COLORS.length - 1);
                    color = DEPTH_COLORS[d]?.fill || '#94a3b8';
                } else if (this.groupMode === 'book') {
                    key = n.book;
                    label = n.book;
                    color = bookColor(n.book_order || 1).fill;
                } else if (this.groupMode === 'author') {
                    key = BOOK_AUTHORS[n.book] || 'Paul';
                    label = key;
                    color = AUTHOR_COLORS[key]?.fill || '#94a3b8';
                } else if (this.groupMode === 'era') {
                    key = BOOK_ERAS[n.book] || 'Early Church';
                    label = key;
                    color = ERA_COLORS[key]?.fill || '#94a3b8';
                }
                if (!groups.has(key)) groups.set(key, { sumX: 0, sumY: 0, count: 0, color, label });
                const g = groups.get(key);
                g.sumX += n.x; g.sumY += n.y; g.count++;
            }
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            for (const [, g] of groups) {
                if (g.count < 2) continue;
                const cx = g.sumX / g.count;
                const cy = g.sumY / g.count;
                // Scale label by cluster size, capped
                const labelSize = Math.min(16 + g.count * 1.5, 40) / this.zoom;
                const screenLabelSize = labelSize * this.zoom;
                if (screenLabelSize < 8) continue; // too small to read
                ctx.font = `700 ${labelSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
                const offsetY = -30 / this.zoom;
                ctx.globalAlpha = 0.2;
                ctx.fillStyle = 'rgba(0,0,0,0.4)';
                ctx.fillText(g.label, cx + 1, cy + offsetY + 1);
                ctx.globalAlpha = 0.3;
                ctx.fillStyle = g.color;
                ctx.fillText(g.label, cx, cy + offsetY);
            }
            ctx.globalAlpha = 1;
        }

        ctx.restore();
        ctx.restore();
    }

    resetView() {
        this.camX = 0;
        this.camY = 0;
        this.zoom = 1;
        this._draw();
    }

    // Compute target positions for each node based on groupMode
    _getGroupTargets(nodes) {
        const mode = this.groupMode;
        const targets = new Array(nodes.length);
        const spread = Math.max(400, nodes.length * 4); // generous spread for group separation

        if (mode === 'depth') {
            // Concentric rings by hop distance
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const d = n.depth || 1;
                const ringR = d * spread * 0.4;
                const angle = (i / nodes.length) * Math.PI * 2;
                targets[i] = { x: Math.cos(angle) * ringR, y: Math.sin(angle) * ringR };
            }
        } else if (mode === 'testament') {
            // OT left, NT right
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const xOff = n.testament === 'OT' ? -spread * 0.5 : spread * 0.5;
                const order = n.book_order || 1;
                const yNorm = n.testament === 'OT' ? (order - 20) / 20 : (order - 55) / 12;
                targets[i] = { x: xOff, y: yNorm * spread * 0.6 };
            }
        } else if (mode === 'book') {
            // Each book gets a position around a large circle, ordered by book_order
            const bookOrders = [...new Set(nodes.map(n => n.book_order || 1))].sort((a, b) => a - b);
            const bookAngle = {};
            bookOrders.forEach((bo, i) => {
                bookAngle[bo] = (i / bookOrders.length) * Math.PI * 2 - Math.PI / 2;
            });
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const angle = bookAngle[n.book_order || 1] || 0;
                const r = spread * 0.6;
                targets[i] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
            }
        } else if (mode === 'genre') {
            // Genre clusters arranged in a circle
            const genreList = ['law', 'history', 'wisdom', 'major_prophet', 'minor_prophet', 'gospel', 'history_nt', 'epistle', 'apocalyptic'];
            const genreAngle = {};
            genreList.forEach((g, i) => {
                genreAngle[g] = (i / genreList.length) * Math.PI * 2 - Math.PI / 2;
            });
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const genre = BOOK_GENRES[n.book] || 'epistle';
                const angle = genreAngle[genre] || 0;
                const r = spread * 0.55;
                targets[i] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
            }
        } else if (mode === 'author') {
            // Each author gets a position around a circle
            const authors = [...new Set(nodes.filter(n => !n.isCenter).map(n => BOOK_AUTHORS[n.book] || 'Paul'))];
            const authorAngle = {};
            authors.forEach((a, i) => {
                authorAngle[a] = (i / authors.length) * Math.PI * 2 - Math.PI / 2;
            });
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const author = BOOK_AUTHORS[n.book] || 'Paul';
                const angle = authorAngle[author] || 0;
                const r = spread * 0.55;
                targets[i] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
            }
        } else if (mode === 'era') {
            // Eras arranged in chronological order around a circle
            const eraAngle = {};
            ERA_LIST.forEach((e, i) => {
                eraAngle[e] = (i / ERA_LIST.length) * Math.PI * 2 - Math.PI / 2;
            });
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                if (n.isCenter) { targets[i] = { x: 0, y: 0 }; continue; }
                const era = BOOK_ERAS[n.book] || 'Early Church';
                const angle = eraAngle[era] || 0;
                const r = spread * 0.55;
                targets[i] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
            }
        }

        return targets;
    }
}
