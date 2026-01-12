#!/bin/bash

# Setup script to copy generated documentation to demo folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPOS_DIR="$PROJECT_ROOT/test_repos"
DEMO_REPOS_DIR="$SCRIPT_DIR/repos"

echo "Setting up CodeWiki demo..."
echo "Copying generated documentation..."

mkdir -p "$DEMO_REPOS_DIR"

# List of repos to include
repos=("fastapi" "flask" "nextjs" "react" "go" "vscode" "kubernetes" "tensorflow" "pytorch")

for repo in "${repos[@]}"; do
    repo_path="$REPOS_DIR/$repo"
    demo_repo_path="$DEMO_REPOS_DIR/$repo"
    
    if [ -d "$repo_path/docs" ]; then
        echo "  Copying $repo..."
        mkdir -p "$demo_repo_path"
        cp -r "$repo_path/docs"/* "$demo_repo_path/" 2>/dev/null || true
    else
        echo "  Warning: $repo/docs not found, skipping..."
    fi
done

echo "Done! Demo is ready to deploy."
echo ""
echo "To deploy to Vercel:"
echo "  cd $SCRIPT_DIR"
echo "  vercel --prod"

