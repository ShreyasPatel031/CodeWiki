# CodeWiki Demo

A simple demo page for viewing CodeWiki-generated documentation for multiple repositories.

## Features

- **Left Sidebar**: Repository switcher
- **Right Panes**: 
  - Top: Architecture diagram (Mermaid)
  - Bottom: Documentation (Markdown)

## Setup

1. Copy generated documentation to this folder:
```bash
# From the CodeWiki root directory
./setup-demo.sh
```

2. Deploy to Vercel:
```bash
npm i -g vercel
vercel login
vercel --prod
```

## Structure

```
demo/
├── index.html          # Main demo page
├── package.json        # Vercel configuration
├── vercel.json         # Vercel routing
├── api/
│   └── repo/
│       └── index.js    # API route for serving repo data
└── repos/              # Generated docs (created by setup script)
    ├── fastapi/
    ├── flask/
    └── ...
```

## Customization

Update the `repos` array in `index.html` to add/remove repositories.





