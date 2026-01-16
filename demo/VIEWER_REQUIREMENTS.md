# CodeWiki Viewer Requirements

## What the Viewer Handles Automatically

The viewer is designed to work with ANY repo without code changes:

1. **Auto Node-to-Module Mapping**: Diagram nodes are automatically linked to modules
   - Matches by node ID to module key
   - Matches by node label to module name  
   - Fuzzy matching for partial matches
   - NO click statements required in Mermaid

2. **Mermaid Sanitization**: Common diagram issues are auto-fixed:
   - Edge labels with numbered lists (e.g., `|1. Action|` → `|Action|`)
   - Special characters in labels
   - Subgraph names with spaces

3. **Fallback Rendering**: If sanitization fails, tries original diagram

## Required Files for Each Repository

Every repo in `demo/repos/[repo-name]/` MUST have:

| File | Required | Description |
|------|----------|-------------|
| `metadata.json` | ✅ Yes | Generation info, repo path |
| `module_tree.json` | ✅ Yes | Module hierarchy structure |
| `overview.md` | ✅ Yes | Main overview with Mermaid diagram |
| `[module].md` | Optional | Per-module documentation |

## File Format Requirements

### 1. metadata.json
```json
{
  "generation_info": {
    "repo_path": "/path/to/repo",
    "timestamp": "2026-01-16T12:00:00Z"
  }
}
```

### 2. module_tree.json
```json
{
  "module_name": {
    "path": "path/to/module",
    "components": ["Component1", "Component2"],
    "children": {}
  }
}
```

### 3. overview.md
Must contain a Mermaid diagram with:
- `graph TD` or `flowchart TD` declaration
- Node definitions: `NodeId["Node Label"]`
- Click statements for navigation: `click NodeId "module_name.md"`
- Edges between nodes: `A --> B`

Example:
```markdown
# Repository Overview

## Architecture

\`\`\`mermaid
graph TD
    A["Module A"]
    B["Module B"]
    A --> B
    click A "module_a.md"
    click B "module_b.md"
\`\`\`
```

## Viewer Features Checklist

### Core Features
- [ ] Loads metadata.json
- [ ] Loads module_tree.json
- [ ] Loads overview.md
- [ ] Extracts Mermaid diagram from overview
- [ ] Renders Mermaid diagram
- [ ] Displays documentation (right pane)
- [ ] Clickable nodes with blue border
- [ ] Node expansion (inline subgraph)
- [ ] Collapse button in expanded subgraphs
- [ ] Back button navigation
- [ ] Keyboard shortcuts (1-9, 0/c, Escape)

### Zoom/Pan Features
- [ ] Zoom in/out buttons
- [ ] Mouse wheel zoom
- [ ] Drag to pan
- [ ] Reset zoom button
- [ ] Fit to view button
- [ ] Touch support (pinch zoom, drag pan)

### Error Handling
- [ ] Shows error if repo not found
- [ ] Shows error if files missing
- [ ] Shows error if Mermaid render fails
- [ ] Graceful fallback for missing module docs

## Testing Procedure

### Step 1: Verify File Structure
```bash
ls -la demo/repos/[repo-name]/
# Must see: metadata.json, module_tree.json, overview.md
```

### Step 2: Verify File Contents
```bash
# Check metadata.json is valid JSON
cat demo/repos/[repo-name]/metadata.json | python3 -m json.tool

# Check module_tree.json is valid JSON
cat demo/repos/[repo-name]/module_tree.json | python3 -m json.tool

# Check overview.md has mermaid diagram
grep -A 5 "mermaid" demo/repos/[repo-name]/overview.md
```

### Step 3: Start Local Server
```bash
cd demo && python3 -m http.server 3005
```

### Step 4: Browser Tests
1. Navigate to `http://localhost:3005/viewer.html?repo=[repo-name]`
2. Verify diagram renders
3. Verify documentation displays
4. Click each node - verify expansion works
5. Click collapse button - verify it works
6. Test zoom controls
7. Test keyboard shortcuts
8. Test back button

### Step 5: Console Error Check
Open browser DevTools Console and verify:
- No JavaScript errors
- No 404 errors for files
- No Mermaid render errors

## Common Issues and Fixes

### Issue: "No diagram available"
- Check overview.md contains ```mermaid block
- Check mermaid syntax is valid

### Issue: Nodes not clickable
- Check click statements in Mermaid: `click NodeId "file.md"`
- Check module files exist

### Issue: 404 errors
- Check file names match exactly (case-sensitive)
- Check files are in correct directory

### Issue: Diagram doesn't render
- Check Mermaid syntax (use online Mermaid editor to validate)
- Check for special characters that need escaping

## Automated Verification

**ALWAYS run the verification script before claiming a repo works:**

```bash
# Verify single repo
python scripts/verify_viewer.py <repo-name>

# Verify all repos
python scripts/verify_viewer.py --all
```

The script checks:
- ✅ Required files exist
- ✅ JSON files are valid
- ✅ Mermaid diagram exists
- ✅ Node-to-module mapping potential
- ✅ Module documentation files

**Exit code 0 = Compatible, Exit code 1 = Not compatible**
