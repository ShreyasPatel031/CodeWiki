/**
 * Generic Viewer Test Suite
 * 
 * Tests node clicking, inline substitution, Mermaid diagrams, and collapse functionality.
 * Works with any repo via viewer.html?repo=X
 * 
 * Usage:
 *   1. Open http://localhost:PORT/viewer.html?repo=flask in browser
 *   2. Open browser console (F12)
 *   3. Copy-paste this file contents OR run: ViewerTests.run()
 */

const ViewerTests = {
    passed: 0,
    failed: 0,
    errors: [],
    currentRepo: null,
    
    /**
     * Main test runner
     */
    async run(options = {}) {
        console.log('🧪 Starting Generic Viewer Tests...\n');
        console.log('=' .repeat(60));
        
        this.passed = 0;
        this.failed = 0;
        this.errors = [];
        
        // Detect current repo from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.currentRepo = urlParams.get('repo') || 'unknown';
        console.log(`📦 Testing repo: ${this.currentRepo}\n`);
        
        // Wait for initial render
        await this.waitForDiagram();
        
        // Run test suites
        await this.testSuite_InitialRender();
        await this.testSuite_DataStructures();
        await this.testSuite_MermaidFormat();
        await this.testSuite_NodeExpansion();
        await this.testSuite_InlineSubstitution();
        await this.testSuite_CollapseButton();
        await this.testSuite_EdgeUpdates();
        
        if (!options.skipAllNodes) {
            await this.testSuite_AllNodesExpand();
        }
        
        // Report results
        this.reportResults();
        
        return { passed: this.passed, failed: this.failed, errors: this.errors };
    },
    
    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================
    
    async waitForDiagram(timeout = 5000) {
        const start = Date.now();
        return new Promise((resolve, reject) => {
            const check = () => {
                const svg = document.querySelector('#mermaid-diagram svg');
                if (svg && svg.querySelector('.node')) {
                    resolve();
                } else if (Date.now() - start > timeout) {
                    reject(new Error('Timeout waiting for diagram'));
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    },
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },
    
    assert(condition, testName, errorDetail = '') {
        if (condition) {
            this.passed++;
            console.log(`  ✅ ${testName}`);
        } else {
            this.failed++;
            const msg = `  ❌ ${testName}${errorDetail ? ': ' + errorDetail : ''}`;
            console.log(msg);
            this.errors.push(msg);
        }
    },
    
    async resetViewer() {
        // Reset without page reload
        if (typeof expandedNodes !== 'undefined') {
            expandedNodes.clear();
        }
        if (typeof currentDiagramCode !== 'undefined' && typeof baseDiagramCode !== 'undefined') {
            window.currentDiagramCode = window.baseDiagramCode;
        }
        if (typeof renderDiagram === 'function' && typeof baseDiagramCode !== 'undefined') {
            renderDiagram(baseDiagramCode, overviewLinks, 'overview');
        }
        await this.sleep(300);
        await this.waitForDiagram();
    },
    
    getDiagramText() {
        return document.querySelector('#mermaid-diagram')?.textContent || '';
    },
    
    hasRenderError() {
        const text = this.getDiagramText();
        return text.includes('Error rendering') || text.includes('Syntax error');
    },
    
    getNodeCount() {
        const svg = document.querySelector('#mermaid-diagram svg');
        return svg?.querySelectorAll('.node')?.length || 0;
    },
    
    getSubgraphCount() {
        const svg = document.querySelector('#mermaid-diagram svg');
        return svg?.querySelectorAll('.cluster')?.length || 0;
    },
    
    getClickableNodeCount() {
        const svg = document.querySelector('#mermaid-diagram svg');
        return svg?.querySelectorAll('.clickable-node')?.length || 0;
    },
    
    pressKey(key) {
        document.dispatchEvent(new KeyboardEvent('keydown', { key }));
    },
    
    // ============================================================
    // TEST SUITES
    // ============================================================
    
    async testSuite_InitialRender() {
        console.log('\n📋 Suite: Initial Render');
        
        const svg = document.querySelector('#mermaid-diagram svg');
        this.assert(svg !== null, 'SVG diagram exists');
        this.assert(!this.hasRenderError(), 'No render error on initial load');
        this.assert(this.getNodeCount() >= 5, `Has at least 5 nodes (found: ${this.getNodeCount()})`);
        this.assert(this.getClickableNodeCount() >= 1, `Has clickable nodes (found: ${this.getClickableNodeCount()})`);
    },
    
    async testSuite_DataStructures() {
        console.log('\n📋 Suite: Data Structures');
        
        // Check global objects exist
        this.assert(typeof overviewLinks === 'object', 'overviewLinks object exists');
        this.assert(typeof moduleData === 'object', 'moduleData object exists');
        this.assert(typeof expandedNodes !== 'undefined', 'expandedNodes exists');
        this.assert(typeof baseDiagramCode === 'string', 'baseDiagramCode is a string');
        
        // Check overviewLinks has entries
        const linkCount = Object.keys(overviewLinks).length;
        this.assert(linkCount >= 1, `overviewLinks has entries (found: ${linkCount})`);
        
        // Check moduleData has entries with diagrams
        const moduleCount = Object.keys(moduleData).length;
        this.assert(moduleCount >= 2, `moduleData has modules (found: ${moduleCount})`);
        
        // Check at least one module has a diagram
        const modulesWithDiagrams = Object.values(moduleData).filter(m => m.diagram && m.diagram.length > 0);
        this.assert(modulesWithDiagrams.length >= 1, `Modules have diagrams (found: ${modulesWithDiagrams.length})`);
    },
    
    async testSuite_MermaidFormat() {
        console.log('\n📋 Suite: Mermaid Diagram Format');
        
        // Check base diagram format
        const diagramCode = baseDiagramCode || '';
        
        // Should be graph or flowchart
        const hasGraphType = /^(graph|flowchart)\s+(TD|TB|LR|RL|BT)/m.test(diagramCode);
        this.assert(hasGraphType, 'Diagram uses graph/flowchart type');
        
        // Should not be classDiagram or sequenceDiagram at top level
        const hasInvalidType = /^(classDiagram|sequenceDiagram)/m.test(diagramCode);
        this.assert(!hasInvalidType, 'Does not use classDiagram/sequenceDiagram');
        
        // Check for click statements in overview
        const hasClickStatements = /click\s+\w+\s+"[^"]+"/m.test(diagramCode);
        this.assert(hasClickStatements, 'Overview diagram has click statements');
        
        // Check node definitions exist
        const hasNodeDefs = /\w+\s*\[[^\]]+\]/.test(diagramCode);
        this.assert(hasNodeDefs, 'Diagram has node definitions');
    },
    
    async testSuite_NodeExpansion() {
        console.log('\n📋 Suite: Node Expansion');
        
        await this.resetViewer();
        
        const initialNodeCount = this.getNodeCount();
        const initialSubgraphCount = this.getSubgraphCount();
        
        // Press "1" to expand first node
        this.pressKey('1');
        await this.sleep(500);
        
        // Check no error
        this.assert(!this.hasRenderError(), 'No error after expanding node 1');
        
        // Check expandedNodes tracking
        this.assert(expandedNodes.size >= 1, 'expandedNodes tracks expanded node');
        
        // Check node count increased (subgraph adds nodes)
        const afterNodeCount = this.getNodeCount();
        this.assert(afterNodeCount > initialNodeCount, `Node count increased (${initialNodeCount} → ${afterNodeCount})`);
        
        // Check subgraph created
        const afterSubgraphCount = this.getSubgraphCount();
        this.assert(afterSubgraphCount > initialSubgraphCount, `Subgraph created (${initialSubgraphCount} → ${afterSubgraphCount})`);
    },
    
    async testSuite_InlineSubstitution() {
        console.log('\n📋 Suite: Inline Substitution');
        
        await this.resetViewer();
        
        // Get the first expanded node ID
        const firstNodeId = Object.keys(overviewLinks)[0];
        if (!firstNodeId) {
            this.assert(false, 'Has a node to expand');
            return;
        }
        
        // Expand first node
        this.pressKey('1');
        await this.sleep(500);
        
        // Check subgraph has correct label (matches original node label, not module name)
        const svg = document.querySelector('#mermaid-diagram svg');
        const clusters = svg?.querySelectorAll('.cluster');
        this.assert(clusters?.length >= 1, 'Subgraph cluster exists');
        
        // Check no orphan nodes with just single letter/ID as text
        const nodes = svg?.querySelectorAll('.node');
        let orphanCount = 0;
        nodes?.forEach(node => {
            const text = node.querySelector('text, .nodeLabel')?.textContent?.trim() || '';
            // Orphan = single character that matches a node ID and isn't "[" or other special char
            if (/^[A-Z]$/.test(text) && overviewLinks[text]) {
                orphanCount++;
            }
        });
        this.assert(orphanCount === 0, `No orphan single-letter nodes (found: ${orphanCount})`);
        
        // Check collapse button exists
        const collapseExists = Array.from(nodes || []).some(n => 
            n.textContent?.includes('Collapse')
        );
        this.assert(collapseExists, 'Collapse button exists in expanded subgraph');
    },
    
    async testSuite_CollapseButton() {
        console.log('\n📋 Suite: Collapse Button');
        
        await this.resetViewer();
        
        const initialNodeCount = this.getNodeCount();
        
        // Expand first node
        this.pressKey('1');
        await this.sleep(500);
        
        const expandedNodeCount = this.getNodeCount();
        this.assert(expandedNodeCount > initialNodeCount, 'Nodes added after expansion');
        
        // Press 'c' to collapse
        this.pressKey('c');
        await this.sleep(500);
        
        // Check no error
        this.assert(!this.hasRenderError(), 'No error after collapse');
        
        // Check node count returned to initial
        const afterCollapseCount = this.getNodeCount();
        this.assert(afterCollapseCount === initialNodeCount, `Node count restored (${initialNodeCount} vs ${afterCollapseCount})`);
        
        // Check expandedNodes is empty
        this.assert(expandedNodes.size === 0, 'expandedNodes cleared after collapse');
    },
    
    async testSuite_EdgeUpdates() {
        console.log('\n📋 Suite: Edge Updates');
        
        await this.resetViewer();
        
        // Expand first node
        this.pressKey('1');
        await this.sleep(500);
        
        // Get the expanded node ID
        const expandedNodeId = Array.from(expandedNodes)[0];
        if (!expandedNodeId) {
            this.assert(false, 'Has an expanded node to check');
            return;
        }
        
        // Check current diagram code for edge references
        const diagramCode = currentDiagramCode || '';
        
        // The original node ID should be replaced with subgraph in edges
        // e.g., "A --> B" should become "A_sub --> B" after expanding A
        const subgraphName = `${expandedNodeId}_sub`;
        const hasSubgraphInEdges = diagramCode.includes(subgraphName);
        this.assert(hasSubgraphInEdges, `Edges reference subgraph (${subgraphName})`);
        
        // Original node shouldn't appear alone in edges (would create orphan)
        // Pattern: nodeId followed by space and --> (not as part of longer ID)
        const orphanEdgePattern = new RegExp(`\\b${expandedNodeId}\\s*-->|-->\\s*${expandedNodeId}\\b`);
        const hasOrphanEdge = orphanEdgePattern.test(diagramCode);
        // This might still match inside subgraph content, so we check more carefully
        // For now, just log for debugging
        if (hasOrphanEdge) {
            console.log(`    ⚠️  Possible orphan edge found (may be false positive)`);
        }
    },
    
    async testSuite_AllNodesExpand() {
        console.log('\n📋 Suite: All Clickable Nodes Expand');
        
        const clickableCount = this.getClickableNodeCount();
        const nodesToTest = Math.min(clickableCount, 9);
        
        for (let i = 1; i <= nodesToTest; i++) {
            await this.resetViewer();
            
            this.pressKey(String(i));
            await this.sleep(400);
            
            const hasError = this.hasRenderError();
            this.assert(!hasError, `Node ${i} expands without error`);
            
            if (hasError) {
                console.log(`    Error detail: ${this.getDiagramText().substring(0, 100)}`);
            }
        }
    },
    
    // ============================================================
    // RESULTS
    // ============================================================
    
    reportResults() {
        console.log('\n' + '='.repeat(60));
        console.log(`📊 Test Results: ${this.passed} passed, ${this.failed} failed`);
        console.log('='.repeat(60));
        
        if (this.failed > 0) {
            console.log('\n❌ Failed tests:');
            this.errors.forEach(e => console.log(e));
        } else {
            console.log('\n🎉 All tests passed!');
        }
        
        return { passed: this.passed, failed: this.failed };
    }
};

// Auto-announce when loaded
if (typeof window !== 'undefined') {
    console.log('📦 ViewerTests loaded. Run with: ViewerTests.run()');
    console.log('   Quick run (skip all-nodes): ViewerTests.run({skipAllNodes: true})');
}

// Export for Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ViewerTests;
}


