# Deployment Guide

## Quick Deploy to Vercel

1. **Install Vercel CLI** (if not already installed):
```bash
npm i -g vercel
```

2. **Login to Vercel**:
```bash
vercel login
```

3. **Navigate to demo directory**:
```bash
cd /Users/shreyaspatel/CodeWiki/demo
```

4. **Run setup script** (copies generated docs):
```bash
./setup-demo.sh
```

5. **Deploy to Vercel**:
```bash
vercel --prod
```

Follow the prompts:
- Set up and deploy? **Yes**
- Which scope? Select your account
- Link to existing project? **No**
- Project name: **codewiki-demo** (or your choice)
- Directory: **./** (current directory)
- Override settings? **No**

## After Deployment

Your demo will be available at: `https://codewiki-demo.vercel.app` (or your custom domain)

## Updating Documentation

When you regenerate documentation for repos:

1. Run the setup script again:
```bash
./setup-demo.sh
```

2. Redeploy:
```bash
vercel --prod
```

## Project Settings

- **Framework Preset**: Other
- **Build Command**: (leave empty)
- **Output Directory**: ./
- **Install Command**: (leave empty)

## Environment Variables

None required for basic setup.



