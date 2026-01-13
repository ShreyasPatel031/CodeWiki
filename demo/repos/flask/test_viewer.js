/**
 * Automated tests for the Flask viewer
 * 
 * This script tests node clicking and subgraph expansion functionality.
 * Run with: node test_viewer.js (requires puppeteer)
 * 
 * Or run manually in browser console at http://localhost:3003/index.html
 */

// ============================================================
// BROWSER CONSOLE TEST SUITE
// Copy and paste this into the browser console to run tests
// ============================================================

const ViewerTests = {
    passed: 0,
    failed: 0,
    errors: [],
    
    async run() {
        console.log('🧪 Starting Viewer Tests...\n');
        this.passed = 0;
        this.failed = 0;
        this.errors = [];
        
        // Wait for page to be ready
        await this.waitForDiagram();
        
        // Run all tests
        await this.testInitialRender();
        await this.testNodeMappings();
        await this.testFirstLevelExpansion();
        await this.testSecondLevelExpansion();
        await this.testMultipleExpansions();
        await this.testAllNodes();
        
        // Report results
        this.reportResults();
    },
    
    async waitForDiagram() {
        return new Promise((resolve) => {
            const check = () => {
                const svg = document.querySelector('#mermaid-diagram svg');
                if (svg) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    },
    
    assert(condition, testName, errorMsg = '') {
        if (condition) {
            this.passed++;
            console.log(`✅ ${testName}`);
        } else {
            this.failed++;
            const msg = `❌ ${testName}${errorMsg ? ': ' + errorMsg : ''}`;
            console.log(msg);
            this.errors.push(msg);
        }
    },
    
    async testInitialRender() {
        console.log('\n📋 Test: Initial Render');
        
        // Check diagram exists
        const svg = document.querySelector('#mermaid-diagram svg');
        this.assert(svg !== null, 'Diagram SVG exists');
        
        // Check no error message
        const errorText = document.querySelector('#mermaid-diagram')?.textContent || '';
        this.assert(!errorText.includes('Error rendering'), 'No render error on initial load');
        
        // Check nodes exist
        const nodes = svg?.querySelectorAll('.node') || [];
        this.assert(nodes.length >= 10, `Has at least 10 nodes (found: ${nodes.length})`);
    },
    
    async testNodeMappings() {
        console.log('\n📋 Test: Node Mappings');
        
        // Check overviewLinks exists
        this.assert(typeof overviewLinks === 'object', 'overviewLinks object exists');
        
        // Check moduleData exists
        this.assert(typeof moduleData === 'object', 'moduleData object exists');
        
        // Check key modules have data
        const expectedModules = ['flask_app', 'flask_config', 'flask_blueprints'];
        for (const mod of expectedModules) {
            this.assert(
                moduleData[mod] !== undefined, 
                `moduleData contains ${mod}`
            );
            this.assert(
                moduleData[mod]?.diagram?.length > 0,
                `${mod} has a diagram`
            );
        }
    },
    
    async testFirstLevelExpansion() {
        console.log('\n📋 Test: First Level Expansion (Node A)');
        
        // Reset to clean state
        window.location.hash = '';
        await this.reload();
        await this.waitForDiagram();
        
        // Capture console errors
        const consoleErrors = [];
        const originalError = console.error;
        console.error = (...args) => {
            consoleErrors.push(args.join(' '));
            originalError.apply(console, args);
        };
        
        // Simulate pressing "1" to expand node A
        const event = new KeyboardEvent('keydown', { key: '1' });
        document.dispatchEvent(event);
        
        // Wait for re-render
        await this.sleep(500);
        
        // Restore console
        console.error = originalError;
        
        // Check for parse errors
        const diagramText = document.querySelector('#mermaid-diagram')?.textContent || '';
        const hasError = diagramText.includes('Error rendering') || diagramText.includes('Syntax error');
        this.assert(!hasError, 'No parse error after expanding node A', diagramText.substring(0, 100));
        
        // Check subgraph exists
        const svg = document.querySelector('#mermaid-diagram svg');
        const subgraphs = svg?.querySelectorAll('.cluster') || [];
        this.assert(subgraphs.length >= 1, `Subgraph created after expansion (found: ${subgraphs.length})`);
        
        // Check expandedNodes tracking
        this.assert(expandedNodes.has('A'), 'Node A tracked in expandedNodes');
    },
    
    async testSecondLevelExpansion() {
        console.log('\n📋 Test: Second Level (Nested) Expansion');
        
        // Reset to clean state
        await this.reload();
        await this.waitForDiagram();
        
        // First expand node A
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '1' }));
        await this.sleep(500);
        
        // Then try to expand node 2 (should be a nested node or another top-level)
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '2' }));
        await this.sleep(500);
        
        // Check for parse errors
        const diagramText = document.querySelector('#mermaid-diagram')?.textContent || '';
        const hasError = diagramText.includes('Error rendering') || diagramText.includes('Syntax error');
        this.assert(!hasError, 'No parse error after second expansion', diagramText.substring(0, 100));
    },
    
    async testMultipleExpansions() {
        console.log('\n📋 Test: Multiple Simultaneous Expansions');
        
        // Reset
        await this.reload();
        await this.waitForDiagram();
        
        // Expand nodes 1, 2, 3
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '1' }));
        await this.sleep(300);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '3' }));
        await this.sleep(300);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: '5' }));
        await this.sleep(500);
        
        // Check for errors
        const diagramText = document.querySelector('#mermaid-diagram')?.textContent || '';
        const hasError = diagramText.includes('Error rendering') || diagramText.includes('Syntax error');
        this.assert(!hasError, 'No parse error with multiple expansions');
        
        // Check multiple subgraphs exist
        const svg = document.querySelector('#mermaid-diagram svg');
        const subgraphs = svg?.querySelectorAll('.cluster') || [];
        this.assert(subgraphs.length >= 2, `Multiple subgraphs created (found: ${subgraphs.length})`);
    },
    
    async testAllNodes() {
        console.log('\n📋 Test: All Clickable Nodes');
        
        // Test each node 1-9
        for (let i = 1; i <= 9; i++) {
            await this.reload();
            await this.waitForDiagram();
            
            document.dispatchEvent(new KeyboardEvent('keydown', { key: String(i) }));
            await this.sleep(400);
            
            const diagramText = document.querySelector('#mermaid-diagram')?.textContent || '';
            const hasError = diagramText.includes('Error rendering') || diagramText.includes('Syntax error');
            this.assert(!hasError, `Node ${i} expands without error`);
        }
    },
    
    async reload() {
        // Reset state without full page reload
        if (typeof expandedNodes !== 'undefined') {
            expandedNodes.clear();
        }
        if (typeof currentDiagramCode !== 'undefined' && typeof baseDiagramCode !== 'undefined') {
            currentDiagramCode = baseDiagramCode;
        }
        if (typeof renderDiagram === 'function' && typeof baseDiagramCode !== 'undefined') {
            renderDiagram(baseDiagramCode, overviewLinks, 'overview');
        }
        await this.sleep(200);
    },
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },
    
    reportResults() {
        console.log('\n' + '='.repeat(50));
        console.log(`📊 Test Results: ${this.passed} passed, ${this.failed} failed`);
        console.log('='.repeat(50));
        
        if (this.failed > 0) {
            console.log('\n❌ Failed tests:');
            this.errors.forEach(e => console.log('  ' + e));
        } else {
            console.log('\n🎉 All tests passed!');
        }
        
        return { passed: this.passed, failed: this.failed, errors: this.errors };
    }
};

// Export for Node.js / Puppeteer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ViewerTests;
}

// Auto-run if in browser
if (typeof window !== 'undefined' && window.document) {
    console.log('ViewerTests loaded. Run with: ViewerTests.run()');
}

