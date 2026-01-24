<h1 align="center">CodeWiki</h1>

<p align="center">
  <strong>AI-Powered Repository Documentation Generation</strong>
</p>

<p align="center">
  Generate comprehensive, architecture-aware documentation for large-scale codebases with interactive diagrams and multi-level module exploration.
</p>

<p align="center">
  <a href="https://python.org/"><img alt="Python version" src="https://img.shields.io/badge/python-3.12+-blue?style=flat-square" /></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" /></a>
</p>

<p align="center">
  <a href="#quick-start"><strong>Quick Start</strong></a> •
  <a href="#live-demo"><strong>Live Demo</strong></a> •
  <a href="#generate-documentation"><strong>Generate Docs</strong></a> •
  <a href="#viewer"><strong>Interactive Viewer</strong></a>
</p>

---

## Live Demo

**View pre-generated documentation:**

- **Deployed Demo**: https://codewiki-demo-ldowvzx01-shreyaspatel031s-projects.vercel.app
- **KubeElasti**: https://codewiki-demo-ldowvzx01-shreyaspatel031s-projects.vercel.app/viewer.html?repo=KubeElasti
- **Flask**: https://codewiki-demo-ldowvzx01-shreyaspatel031s-projects.vercel.app/viewer.html?repo=flask

**Run locally:**

```bash
# From the CodeWiki root directory
python3 -m http.server 8080

# Open in browser:
# http://localhost:8080/demo/viewer.html?repo=KubeElasti
# http://localhost:8080/demo/viewer.html?repo=flask
```

---

## Quick Start

### 1. Install CodeWiki

```bash
# Clone the repository
git clone https://github.com/ShreyasPatel031/CodeWiki.git
cd CodeWiki

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
```

### 2. Configure Your API Key

```bash
codewiki config set \
  --api-key YOUR_GEMINI_API_KEY \
  --main-model gemini-2.0-flash \
  --cluster-model gemini-2.0-flash
```

### 3. Generate Documentation

```bash
# Navigate to any repository
cd /path/to/your/repo

# Generate documentation
codewiki generate

# Generate with interactive HTML viewer
codewiki generate --github-pages
```

---

## Generate Documentation

### Basic Usage

```bash
# Generate documentation for current directory
codewiki generate

# Custom output directory
codewiki generate --output ./documentation

# With interactive HTML viewer (for GitHub Pages)
codewiki generate --github-pages

# Create a git branch for documentation
codewiki generate --create-branch

# Full-featured generation
codewiki generate --github-pages --create-branch --verbose
```

### Output Structure

After running `codewiki generate`, you'll get:

```
./docs/
├── overview.md              # Repository overview (start here)
├── module_name.md           # Documentation for each module
├── submodule_name.md        # Sub-module documentation
├── module_tree.json         # Hierarchical module structure
├── first_module_tree.json   # Initial clustering result
├── metadata.json            # Generation metadata
└── index.html               # Interactive viewer (with --github-pages)
```

---

## Viewer

The interactive viewer provides a visual way to explore generated documentation:

### Features

- **Clickable Architecture Diagrams**: Click on modules in the Mermaid diagram to navigate
- **Depth Navigation**: Explore up to 3 levels deep in module hierarchy
- **Breadcrumb Trail**: Track your navigation path
- **Zoom & Pan**: Navigate large diagrams easily
- **Markdown Rendering**: Full markdown support with code highlighting

### Using the Viewer with Generated Docs

After generating documentation with `--github-pages`:

1. **Local Development**:
   ```bash
   cd /path/to/your/repo
   python3 -m http.server 8080
   # Open http://localhost:8080/docs/index.html
   ```

2. **GitHub Pages**: Push the `docs/` folder to your GitHub repo and enable GitHub Pages

3. **Add to Demo**: Copy generated docs to the demo folder:
   ```bash
   # From CodeWiki root
   cp -r /path/to/your/repo/docs demo/repos/your-repo-name
   ```

---

## Pre-Generated Demo Repositories

The `demo/repos/` folder contains pre-generated documentation:

| Repository | Description | Path |
|------------|-------------|------|
| **KubeElasti** | Kubernetes autoscaling operator | `demo/repos/KubeElasti/` |
| **Flask** | Python web framework | `demo/repos/flask/` |

Each contains:
- `overview.md` - Repository overview with architecture diagram
- `*.md` - Module documentation files
- `module_tree.json` - Module hierarchy
- `index.html` - Standalone viewer (optional)

---

## Configuration

### Show Current Config

```bash
codewiki config show
```

### Set Configuration

```bash
codewiki config set \
  --api-key <your-api-key> \
  --base-url <provider-url> \
  --main-model <model-name> \
  --cluster-model <model-name>
```

### Validate Configuration

```bash
codewiki config validate
```

**Supported Models:**
- Google Gemini (default): `gemini-2.0-flash`, `gemini-1.5-pro`
- Anthropic Claude: `claude-sonnet-4`, `claude-3-5-sonnet`
- OpenAI: `gpt-4o`, `gpt-4-turbo`

---

## Project Structure

```
CodeWiki/
├── codewiki/                 # Main package
│   ├── cli/                  # CLI commands
│   │   ├── commands/         # config, generate commands
│   │   └── utils/            # File system, logging utilities
│   └── src/                  # Core implementation
│       ├── be/               # Backend (agents, clustering, analysis)
│       │   ├── agent_tools/  # LLM agent tools
│       │   └── dependency_analyzer/  # Code parsing
│       └── fe/               # Frontend (web interface)
├── demo/                     # Demo viewer and pre-generated docs
│   ├── viewer.html           # Interactive documentation viewer
│   ├── repos/                # Pre-generated repository docs
│   │   ├── KubeElasti/       # KubeElasti documentation
│   │   └── flask/            # Flask documentation
│   └── vercel.json           # Vercel deployment config
├── docker/                   # Docker configuration
├── test_repos/               # Test repositories for development
├── tests/                    # Test suite
└── requirements.txt          # Python dependencies
```

---

## Deployment

### Deploy Demo to Vercel

```bash
cd CodeWiki
npx vercel --prod
```

The demo will be deployed with the pre-generated KubeElasti and Flask documentation.

### Deploy Your Own Docs

1. Generate documentation:
   ```bash
   cd /your/repo
   codewiki generate --github-pages
   ```

2. Copy to demo folder:
   ```bash
   cp -r docs /path/to/CodeWiki/demo/repos/your-repo-name
   ```

3. Deploy:
   ```bash
   cd /path/to/CodeWiki
   npx vercel --prod
   ```

---

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Project architecture details
- Adding support for new languages
- Contributing guidelines
- Testing instructions

---

## Requirements

- **Python 3.12+**
- **LLM API access** (Gemini, Anthropic, or OpenAI)
- **Git** (for branch creation features)

---

## License

MIT License - see [LICENSE](./LICENSE) for details.
