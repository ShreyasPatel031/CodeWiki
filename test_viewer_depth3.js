const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    console.log('Navigating to viewer...');
    await page.goto('http://localhost:8080/demo/viewer.html?repo=KubeElasti');
    await page.waitForTimeout(3000);
    
    console.log('=== STEP 1: Click "Operator Module" ===');
    const operatorNode = await page.$('text="Operator Module"');
    if (operatorNode) {
        await operatorNode.click();
        await page.waitForTimeout(2000);
        console.log('Clicked Operator Module');
    }
    
    await page.screenshot({ path: 'depth_1_operator.png', fullPage: true });
    
    // Find and click "Controller Logic" (operator_controller)
    console.log('\n=== STEP 2: Looking for "Controller Logic" or "Operator Controller" ===');
    const allNodes = await page.$$('.node');
    for (const node of allNodes) {
        const text = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => '');
        const id = await node.getAttribute('id');
        const classes = await node.getAttribute('class');
        if (text.includes('Controller') || text.includes('controller')) {
            console.log(`Found: "${text}" id="${id}" clickable=${classes?.includes('clickable-node')}`);
        }
    }
    
    // Click on "Controller Logic"
    const controllerNode = await page.$('text="Controller Logic"');
    if (controllerNode) {
        console.log('\n=== STEP 3: Clicking "Controller Logic" ===');
        await controllerNode.click();
        await page.waitForTimeout(2000);
        console.log('Clicked Controller Logic');
        
        await page.screenshot({ path: 'depth_2_controller.png', fullPage: true });
        
        // Now check for depth 3 nodes
        console.log('\n=== STEP 4: Looking for depth 3 nodes (elastiservice_controller, ops_informer) ===');
        const depth3Nodes = await page.$$('.node');
        let foundElastiController = false;
        let foundOpsInformer = false;
        
        for (const node of depth3Nodes) {
            const text = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => '');
            const id = await node.getAttribute('id');
            const classes = await node.getAttribute('class');
            const isClickable = classes?.includes('clickable-node');
            
            if (text.toLowerCase().includes('elasti') || text.toLowerCase().includes('ops') || 
                text.toLowerCase().includes('informer') || text.toLowerCase().includes('reconciler')) {
                console.log(`DEPTH 3 NODE: "${text}" id="${id}" clickable=${isClickable}`);
                if (text.toLowerCase().includes('elasti')) foundElastiController = true;
                if (text.toLowerCase().includes('ops')) foundOpsInformer = true;
            }
        }
        
        if (!foundElastiController && !foundOpsInformer) {
            console.log('!!! NO DEPTH 3 NODES FOUND (elastiservice_controller, ops_informer) !!!');
            
            // List ALL nodes to see what we have
            console.log('\n=== ALL NODES AFTER CLICKING CONTROLLER ===');
            for (const node of depth3Nodes) {
                const text = await node.$eval('text, .nodeLabel', el => el.textContent.trim()).catch(() => '');
                const id = await node.getAttribute('id');
                const classes = await node.getAttribute('class');
                console.log(`  "${text}" id="${id}" clickable=${classes?.includes('clickable-node')}`);
            }
        }
    } else {
        console.log('Could not find "Controller Logic" node');
    }
    
    await browser.close();
    console.log('\nDone.');
})();
