#!/usr/bin/env node
/**
 * Automated test runner for Flask viewer using Puppeteer
 * 
 * Usage: 
 *   npm install puppeteer  # if not installed
 *   node run_tests.js
 * 
 * Make sure the server is running at localhost:3003 first:
 *   python3 -m http.server 3003
 */

const puppeteer = require('puppeteer');

const VIEWER_URL = 'http://localhost:3003/index.html';

async function runTests() {
    console.log('🚀 Starting automated viewer tests...\n');
    
    const browser = await puppeteer.launch({ 
        headless: 'new',
        args: ['--no-sandbox']
    });
    
    const page = await browser.newPage();
    
    // Collect console errors
    const consoleErrors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });
    
    let passed = 0;
    let failed = 0;
    const errors = [];
    
    function assert(condition, testName, errorMsg = '') {
        if (condition) {
            passed++;
            console.log(`✅ ${testName}`);
        } else {
            failed++;
            const msg = `❌ ${testName}${errorMsg ? ': ' + errorMsg : ''}`;
            console.log(msg);
            errors.push(msg);
        }
    }
    
    try {
        // Navigate to viewer
        console.log('📋 Test: Initial Load');
        await page.goto(VIEWER_URL, { waitUntil: 'networkidle0' });
        await page.waitForSelector('#mermaid-diagram svg', { timeout: 10000 });
        
        // Check initial render
        const hasInitialSvg = await page.$('#mermaid-diagram svg') !== null;
        assert(hasInitialSvg, 'Initial diagram renders');
        
        const initialContent = await page.$eval('#mermaid-diagram', el => el.textContent);
        assert(!initialContent.includes('Error rendering'), 'No initial render error');
        
        // Check node count
        const nodeCount = await page.$$eval('#mermaid-diagram svg .node', nodes => nodes.length);
        assert(nodeCount >= 10, `Has at least 10 nodes (found: ${nodeCount})`);
        
        // Test moduleData exists
        console.log('\n📋 Test: Module Data');
        const hasModuleData = await page.evaluate(() => typeof moduleData === 'object');
        assert(hasModuleData, 'moduleData object exists');
        
        const moduleKeys = await page.evaluate(() => Object.keys(moduleData));
        assert(moduleKeys.length >= 10, `Has at least 10 modules (found: ${moduleKeys.length})`);
        
        // Check diagrams exist for key modules
        const flaskAppHasDiagram = await page.evaluate(() => 
            moduleData.flask_app?.diagram?.length > 0
        );
        assert(flaskAppHasDiagram, 'flask_app has a diagram');
        
        // Test node expansion (pressing "1")
        console.log('\n📋 Test: First Level Expansion');
        await page.keyboard.press('1');
        await page.waitForTimeout(800);
        
        const afterExpand1 = await page.$eval('#mermaid-diagram', el => el.textContent);
        assert(!afterExpand1.includes('Error rendering'), 'Node 1 expands without error');
        
        const subgraphCount1 = await page.$$eval('#mermaid-diagram svg .cluster', g => g.length);
        assert(subgraphCount1 >= 1, `Subgraph created after expansion (found: ${subgraphCount1})`);
        
        // Test nested expansion (pressing "2" after "1")
        console.log('\n📋 Test: Nested Expansion');
        await page.keyboard.press('2');
        await page.waitForTimeout(800);
        
        const afterExpand2 = await page.$eval('#mermaid-diagram', el => el.textContent);
        assert(!afterExpand2.includes('Error rendering'), 'Nested expansion without error');
        
        // Reload and test each node individually
        console.log('\n📋 Test: All Top-Level Nodes (1-9)');
        for (let i = 1; i <= 9; i++) {
            await page.goto(VIEWER_URL, { waitUntil: 'networkidle0' });
            await page.waitForSelector('#mermaid-diagram svg', { timeout: 5000 });
            
            await page.keyboard.press(String(i));
            await page.waitForTimeout(600);
            
            const content = await page.$eval('#mermaid-diagram', el => el.textContent);
            const hasError = content.includes('Error rendering') || content.includes('Syntax error');
            assert(!hasError, `Node ${i} expands without parse error`);
        }
        
        // Test multiple expansions
        console.log('\n📋 Test: Multiple Simultaneous Expansions');
        await page.goto(VIEWER_URL, { waitUntil: 'networkidle0' });
        await page.waitForSelector('#mermaid-diagram svg', { timeout: 5000 });
        
        await page.keyboard.press('1');
        await page.waitForTimeout(400);
        await page.keyboard.press('3');
        await page.waitForTimeout(400);
        await page.keyboard.press('5');
        await page.waitForTimeout(600);
        
        const multiContent = await page.$eval('#mermaid-diagram', el => el.textContent);
        assert(!multiContent.includes('Error rendering'), 'Multiple expansions without error');
        
        const multiSubgraphs = await page.$$eval('#mermaid-diagram svg .cluster', g => g.length);
        assert(multiSubgraphs >= 2, `Multiple subgraphs visible (found: ${multiSubgraphs})`);
        
    } catch (error) {
        console.error('\n💥 Test execution error:', error.message);
        failed++;
        errors.push(error.message);
    }
    
    await browser.close();
    
    // Report
    console.log('\n' + '='.repeat(50));
    console.log(`📊 Results: ${passed} passed, ${failed} failed`);
    console.log('='.repeat(50));
    
    if (consoleErrors.length > 0) {
        console.log('\n⚠️  Console errors during tests:');
        consoleErrors.forEach(e => console.log('  ' + e));
    }
    
    if (failed > 0) {
        console.log('\n❌ Failed tests:');
        errors.forEach(e => console.log('  ' + e));
        process.exit(1);
    } else {
        console.log('\n🎉 All tests passed!');
        process.exit(0);
    }
}

runTests().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
});

