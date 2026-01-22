const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    console.log('Navigating to viewer...');
    await page.goto('http://localhost:8080/demo/viewer.html?repo=KubeElasti');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'final_1_initial.png', fullPage: true });
    console.log('Screenshot 1: Initial state');
    
    // Click Operator Module
    console.log('\n=== CLICK 1: Operator Module ===');
    await page.click('text="Operator Module"');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'final_2_operator_expanded.png', fullPage: true });
    console.log('Screenshot 2: Operator expanded');
    
    // Click Controller Logic (operator_controller)
    console.log('\n=== CLICK 2: Controller Logic ===');
    await page.click('text="Controller Logic"');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'final_3_controller_expanded.png', fullPage: true });
    console.log('Screenshot 3: Controller expanded');
    
    // Check clickable nodes
    const clickableNodes = await page.$$('.clickable-node');
    console.log(`\nClickable nodes at depth 3: ${clickableNodes.length}`);
    
    // Find ElastiService Controller
    const elastiNode = await page.$('text="ElastiService Controller"');
    if (elastiNode) {
        const parent = await elastiNode.evaluateHandle(el => el.closest('.node'));
        const classes = await parent.evaluate(el => el.getAttribute('class') || '');
        console.log(`"ElastiService Controller" node classes: ${classes}`);
        console.log(`Is clickable: ${classes.includes('clickable-node')}`);
        
        if (classes.includes('clickable-node')) {
            console.log('\n=== CLICK 3: ElastiService Controller (Depth 3) ===');
            await parent.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: 'final_4_elasticontroller_clicked.png', fullPage: true });
            console.log('Screenshot 4: ElastiService Controller clicked');
            
            // Check the documentation panel
            const docContent = await page.$eval('#docContent', el => el.textContent.substring(0, 200));
            console.log(`Documentation panel: ${docContent.substring(0, 100)}...`);
        }
    } else {
        console.log('Could not find ElastiService Controller node');
    }
    
    await browser.close();
    console.log('\n✅ Test complete! Check final_*.png files.');
})();
