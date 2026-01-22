const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    console.log('Navigating to viewer...');
    await page.goto('http://localhost:8080/demo/viewer.html?repo=KubeElasti');
    
    // Wait for diagram to render
    await page.waitForTimeout(3000);
    
    // Take screenshot of initial state
    await page.screenshot({ path: 'screenshot_1_initial.png', fullPage: true });
    console.log('Screenshot 1: Initial state saved');
    
    // Find all nodes and clickable nodes
    const allNodes = await page.$$('.node');
    const clickableNodes = await page.$$('.clickable-node');
    
    console.log(`\n=== NODE ANALYSIS ===`);
    console.log(`Total nodes found: ${allNodes.length}`);
    console.log(`Clickable nodes (blue): ${clickableNodes.length}`);
    
    // Get details of all nodes
    console.log('\n=== ALL NODES ===');
    for (let i = 0; i < allNodes.length; i++) {
        const node = allNodes[i];
        const id = await node.getAttribute('id');
        const classes = await node.getAttribute('class');
        const text = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => 'no text');
        const isClickable = classes?.includes('clickable-node');
        console.log(`Node ${i + 1}: id="${id}", text="${text}", clickable=${isClickable}`);
    }
    
    // If there are clickable nodes, click the first one
    if (clickableNodes.length > 0) {
        console.log('\n=== CLICKING FIRST CLICKABLE NODE ===');
        const firstClickable = clickableNodes[0];
        const text = await firstClickable.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => 'unknown');
        console.log(`Clicking: "${text}"`);
        await firstClickable.click();
        await page.waitForTimeout(2000);
        
        // Take screenshot after first click
        await page.screenshot({ path: 'screenshot_2_after_click1.png', fullPage: true });
        console.log('Screenshot 2: After first click saved');
        
        // Check nodes again
        const newClickableNodes = await page.$$('.clickable-node');
        console.log(`Clickable nodes after click: ${newClickableNodes.length}`);
        
        // List new clickable nodes
        console.log('\n=== CLICKABLE NODES AFTER EXPANSION ===');
        for (let i = 0; i < newClickableNodes.length; i++) {
            const node = newClickableNodes[i];
            const id = await node.getAttribute('id');
            const nodeText = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => 'no text');
            console.log(`Clickable ${i + 1}: id="${id}", text="${nodeText}"`);
        }
        
        // Try clicking the second clickable node (should be a child)
        if (newClickableNodes.length > 1) {
            console.log('\n=== CLICKING SECOND CLICKABLE NODE (DEPTH 2) ===');
            const secondClickable = newClickableNodes[1];
            const secondText = await secondClickable.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => 'unknown');
            console.log(`Clicking: "${secondText}"`);
            await secondClickable.click();
            await page.waitForTimeout(2000);
            
            // Take screenshot after second click
            await page.screenshot({ path: 'screenshot_3_after_click2.png', fullPage: true });
            console.log('Screenshot 3: After second click saved');
            
            // Check for depth 3 clickable nodes
            const depth3Nodes = await page.$$('.clickable-node');
            console.log(`Clickable nodes at depth 3: ${depth3Nodes.length}`);
            
            console.log('\n=== CLICKABLE NODES AT DEPTH 3 ===');
            for (let i = 0; i < depth3Nodes.length; i++) {
                const node = depth3Nodes[i];
                const id = await node.getAttribute('id');
                const nodeText = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => 'no text');
                console.log(`Clickable ${i + 1}: id="${id}", text="${nodeText}"`);
            }
        }
    } else {
        console.log('\n!!! NO CLICKABLE NODES FOUND !!!');
    }
    
    await browser.close();
    console.log('\nDone. Check screenshot_*.png files.');
})();
